from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from models import Conversation, Message, Project, User
from auth import get_current_user
from tools.executor import execute_tool
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from database import async_session as _async_session
from routes.chat_crud import _get_convo, _convo_dict, _msg_dict
import httpx
import json
import re
import os

router = APIRouter(prefix="/api/chat", tags=["chat"])

OLLAMA_BASE = "http://localhost:11434"

from location import _get_user_location
from tools.definitions import TOOLS
from tools.system_prompt import build_system_prompt
from utils import resize_image_for_vision, read_file_content


class SendMessageRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    model: str = "qwen3.5:122b"
    project_id: str | None = None
    persona: str | None = None
    attachments: list[dict] | None = None


# ── Chat with Tool Loop ────────────────────────────────────────────────────

@router.post("/send")
async def send_message(req: SendMessageRequest, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Get or create conversation
    if req.conversation_id:
        convo = await _get_convo(req.conversation_id, user_id, db)
    else:
        convo = Conversation(user_id=user_id, model=req.model, project_id=req.project_id)
        db.add(convo)
        await db.commit()
        await db.refresh(convo)

    # Save user message
    user_msg = Message(conversation_id=convo.id, role="user", content=req.message, attachments=req.attachments)
    db.add(user_msg)
    await db.commit()

    # Build message history
    result = await db.execute(select(Message).where(Message.conversation_id == convo.id).order_by(Message.created_at))
    all_msgs = result.scalars().all()

    # System prompt — gather DB data, then delegate to build_system_prompt()
    location, tz = await _get_user_location()

    user_result = await db.execute(select(User).where(User.id == user_id))
    user_obj = user_result.scalar_one_or_none()
    custom_instructions = user_obj.custom_instructions if user_obj else None

    project_system_prompt = None
    project_name = None
    if req.project_id:
        proj_result = await db.execute(select(Project).where(Project.id == req.project_id))
        project = proj_result.scalar_one_or_none()
        if project:
            project_system_prompt = project.system_prompt
            project_name = project.name

    system = build_system_prompt(
        location=location,
        timezone=tz,
        persona=req.persona,
        custom_instructions=custom_instructions,
        project_system_prompt=project_system_prompt,
        project_name=project_name,
    )

    ollama_messages = [{"role": "system", "content": system}]
    for m in all_msgs:
        msg_content = m.content
        msg_images = []
        # If message has attachments, handle images and text files
        if m.attachments:
            for att in m.attachments:
                filepath = att.get("path", "")
                filename = att.get("filename", "")
                mime = att.get("type", "")
                # Image attachments → resize and send as vision input
                if mime.startswith("image/") or filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    if filepath and os.path.exists(filepath):
                        img_b64 = resize_image_for_vision(filepath)
                        if img_b64:
                            msg_images.append(img_b64)
                else:
                    # Text/PDF attachments → read content
                    file_text = read_file_content(filepath, filename)
                    if file_text:
                        msg_content += f"\n\n--- Attached file: {filename} ---\n{file_text}\n--- End of file ---"
        msg_entry = {"role": m.role, "content": msg_content}
        if msg_images:
            msg_entry["images"] = msg_images
        ollama_messages.append(msg_entry)

    convo.updated_at = datetime.now(timezone.utc)
    await db.commit()

    async def generate():
        full_response = ""
        all_artifacts = []
        all_tool_calls = []
        all_images = []
        all_thinking = ""
        messages = list(ollama_messages)
        max_tool_rounds = 8  # Safety limit
        partial_msg_id = None  # Track partial message for incremental saves

        try:
            for round_num in range(max_tool_rounds + 1):
                # Call Ollama
                response_text = ""
                tool_calls = []
                eval_count = 0
                eval_duration = 0

                async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)) as client:
                    payload = {
                        "model": req.model,
                        "messages": messages,
                        "stream": True,
                        "options": {"num_ctx": 32768, "num_predict": 4096},
                        "tools": TOOLS,
                    }
                    async with client.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload) as response:
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)

                                # Stream text tokens to the client
                                if "message" in data:
                                    msg = data["message"]

                                    # Handle thinking tokens (qwen3.5 sends these before tool calls)
                                    if msg.get("thinking"):
                                        all_thinking += msg["thinking"]
                                        yield f"data: {json.dumps({'type': 'thinking', 'content': msg['thinking']})}\n\n"

                                    if msg.get("content"):
                                        chunk = msg["content"]
                                        response_text += chunk
                                        full_response += chunk
                                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

                                        # Save partial content after first token
                                        if not partial_msg_id and full_response:
                                            try:
                                                async with get_db_session() as partial_db:
                                                    partial_msg = Message(
                                                        conversation_id=convo.id,
                                                        role="assistant",
                                                        content=full_response,
                                                        model=req.model,
                                                    )
                                                    partial_db.add(partial_msg)
                                                    await partial_db.commit()
                                                    await partial_db.refresh(partial_msg)
                                                    partial_msg_id = partial_msg.id
                                            except Exception:
                                                pass  # Non-critical, final save is the fallback

                                    # Collect tool calls
                                    if msg.get("tool_calls"):
                                        tool_calls.extend(msg["tool_calls"])

                                if data.get("done"):
                                    eval_count = data.get("eval_count", 0)
                                    eval_duration = data.get("eval_duration", 0)

                            except json.JSONDecodeError:
                                continue

                # Send metrics for this round
                if eval_count:
                    yield f"data: {json.dumps({'type': 'metrics', 'eval_count': eval_count, 'eval_duration': eval_duration})}\n\n"

                # If no tool calls, we're done
                if not tool_calls:
                    break

                # ── Execute tool calls ──────────────────────────────────
                messages.append({"role": "assistant", "content": response_text, "tool_calls": tool_calls})

                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    tool_args = func.get("arguments", {})
                    all_tool_calls.append({"name": tool_name, "arguments": tool_args})

                    # Notify frontend about tool execution
                    yield f"data: {json.dumps({'type': 'tool_start', 'name': tool_name, 'arguments': tool_args})}\n\n"

                    # Execute the tool
                    tool_result = await execute_tool(tool_name, tool_args)

                    # Handle artifacts from create_artifact tool
                    if tool_name == "create_artifact" and tool_result.get("artifact_created"):
                        artifact = {
                            "id": tool_args.get("id", f"artifact-{len(all_artifacts)}"),
                            "type": tool_args.get("type", "code"),
                            "title": tool_args.get("title", "Untitled"),
                            "content": tool_args.get("content", ""),
                            "language": tool_args.get("language", ""),
                        }
                        all_artifacts.append(artifact)
                        yield f"data: {json.dumps({'type': 'artifact', 'artifact': artifact})}\n\n"

                    # If image was generated, send it to the frontend
                    if tool_name in ("generate_image", "edit_image", "security_camera") and tool_result.get("success") and tool_result.get("filename"):
                        img_data = {"filename": tool_result["filename"], "prompt": tool_result.get("prompt", "")}
                        all_images.append(img_data)
                        yield f"data: {json.dumps({'type': 'image', **img_data})}\n\n"

                    yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'result': tool_result})}\n\n"

                    # Add tool result to messages for next round
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(tool_result),
                    })

                # Update partial save after tool round
                if partial_msg_id:
                    try:
                        async with get_db_session() as partial_db:
                            stmt = select(Message).where(Message.id == partial_msg_id)
                            result = await partial_db.execute(stmt)
                            msg = result.scalar_one_or_none()
                            if msg:
                                msg.content = full_response
                                msg.tool_calls = all_tool_calls if all_tool_calls else None
                                msg.artifacts = all_artifacts if all_artifacts else None
                                msg.images = all_images if all_images else None
                                msg.thinking = all_thinking if all_thinking else None
                                await partial_db.commit()
                    except Exception:
                        pass

                # Heartbeat keeps HTTP connection alive during long tool executions
                yield ": heartbeat\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # Also parse any inline code blocks as artifacts
        inline_artifacts = _parse_artifacts(full_response)
        for a in inline_artifacts:
            if not any(ea["content"] == a["content"] for ea in all_artifacts):
                all_artifacts.append(a)
        if inline_artifacts:
            yield f"data: {json.dumps({'type': 'artifacts', 'artifacts': inline_artifacts})}\n\n"

        # Save assistant message (update partial or insert new)
        try:
            async with get_db_session() as save_db:
                if partial_msg_id:
                    # Update the partial message with final content
                    stmt = select(Message).where(Message.id == partial_msg_id)
                    result = await save_db.execute(stmt)
                    assistant_msg = result.scalar_one_or_none()
                    if assistant_msg:
                        assistant_msg.content = full_response
                        assistant_msg.model = req.model
                        assistant_msg.artifacts = all_artifacts if all_artifacts else None
                        assistant_msg.tool_calls = all_tool_calls if all_tool_calls else None
                        assistant_msg.images = all_images if all_images else None
                        assistant_msg.thinking = all_thinking if all_thinking else None
                    else:
                        # Fallback: partial was somehow lost
                        assistant_msg = Message(conversation_id=convo.id, role="assistant", content=full_response, model=req.model, artifacts=all_artifacts if all_artifacts else None, tool_calls=all_tool_calls if all_tool_calls else None, images=all_images if all_images else None, thinking=all_thinking if all_thinking else None)
                        save_db.add(assistant_msg)
                else:
                    # No partial exists (e.g., empty response)
                    assistant_msg = Message(conversation_id=convo.id, role="assistant", content=full_response, model=req.model, artifacts=all_artifacts if all_artifacts else None, tool_calls=all_tool_calls if all_tool_calls else None, images=all_images if all_images else None, thinking=all_thinking if all_thinking else None)
                    save_db.add(assistant_msg)

                if len(all_msgs) <= 1:
                    title = _generate_title(req.message)
                    stmt = select(Conversation).where(Conversation.id == convo.id)
                    result = await save_db.execute(stmt)
                    c = result.scalar_one()
                    c.title = title
                await save_db.commit()
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to save message: {e}'})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'conversation_id': convo.id})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/models")
async def list_models():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            data = resp.json()
            return {"models": [m["name"] for m in data.get("models", [])]}
    except Exception as e:
        return {"models": [], "error": str(e)}


@router.get("/tools/status")
async def tools_status():
    """Check which tools are available and connected."""
    from tools.google_auth import is_google_connected
    return {
        "core": ["execute_code", "web_search", "fetch_url", "get_datetime", "get_weather", "calculator", "create_artifact"],
        "google_connected": is_google_connected(),
        "google_tools": ["gmail_search", "gmail_read", "gmail_send", "calendar_list", "calendar_create"],
    }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _parse_artifacts(text: str) -> list[dict]:
    artifacts = []
    pattern = r'```(\w+)\n(.*?)```'
    for i, match in enumerate(re.finditer(pattern, text, re.DOTALL)):
        lang = match.group(1)
        content = match.group(2).strip()
        if content.count('\n') >= 5:
            artifact_type = "code"
            if lang in ("html", "htm"): artifact_type = "html"
            elif lang == "svg": artifact_type = "svg"
            elif lang == "mermaid": artifact_type = "mermaid"
            artifacts.append({"id": f"artifact-{i}", "type": artifact_type, "title": f"{lang.title()} code", "content": content, "language": lang})
    return artifacts


def _generate_title(message: str) -> str:
    title = message.strip()[:80]
    if len(message) > 80:
        title = title.rsplit(" ", 1)[0] + "..."
    return title


@asynccontextmanager
async def get_db_session():
    async with _async_session() as session:
        yield session
