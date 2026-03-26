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


class ConversationUpdate(BaseModel):
    title: str | None = None
    is_starred: bool | None = None
    project_id: str | None = None


# ── Conversation CRUD ───────────────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.user_id == user_id).order_by(desc(Conversation.updated_at)))
    return [_convo_dict(c) for c in result.scalars().all()]


@router.get("/conversations/{convo_id}")
async def get_conversation(convo_id: str, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    convo = await _get_convo(convo_id, user_id, db)
    result = await db.execute(select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at))
    d = _convo_dict(convo)
    d["messages"] = [_msg_dict(m) for m in result.scalars().all()]
    return d


@router.put("/conversations/{convo_id}")
async def update_conversation(convo_id: str, req: ConversationUpdate, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    convo = await _get_convo(convo_id, user_id, db)
    if req.title is not None: convo.title = req.title
    if req.is_starred is not None: convo.is_starred = req.is_starred
    if req.project_id is not None: convo.project_id = req.project_id if req.project_id else None
    await db.commit()
    await db.refresh(convo)
    return _convo_dict(convo)


@router.delete("/conversations/{convo_id}")
async def delete_conversation(convo_id: str, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    convo = await _get_convo(convo_id, user_id, db)
    await db.delete(convo)
    await db.commit()
    return {"ok": True}


@router.delete("/conversations/{convo_id}/messages/{msg_id}")
async def delete_messages_from(convo_id: str, msg_id: str, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a message and all messages after it (for edit/regenerate)."""
    await _get_convo(convo_id, user_id, db)
    # Get the target message to find its timestamp
    result = await db.execute(select(Message).where(Message.id == msg_id, Message.conversation_id == convo_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Message not found")
    # Delete this message and all after it
    result = await db.execute(
        select(Message).where(Message.conversation_id == convo_id, Message.created_at >= target.created_at)
    )
    for m in result.scalars().all():
        await db.delete(m)
    await db.commit()
    return {"ok": True}


@router.put("/messages/{msg_id}/reaction")
async def set_reaction(msg_id: str, data: dict, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Set thumbs up/down reaction on a message."""
    result = await db.execute(select(Message).where(Message.id == msg_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")
    msg.reaction = data.get("reaction")  # 'up', 'down', or None
    await db.commit()
    return {"ok": True}


@router.get("/search")
async def search_messages(q: str = "", user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Search message content across all conversations."""
    if not q.strip():
        return []
    result = await db.execute(
        select(Message, Conversation)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id, Message.content.ilike(f"%{q}%"))
        .order_by(desc(Message.created_at))
        .limit(20)
    )
    results = []
    for msg, convo in result.all():
        results.append({
            "conversation_id": convo.id,
            "conversation_title": convo.title,
            "message_id": msg.id,
            "role": msg.role,
            "snippet": msg.content[:200],
            "created_at": (msg.created_at.isoformat() + "Z") if msg.created_at else None,
        })
    return results


@router.get("/conversations/{convo_id}/export")
async def export_conversation(convo_id: str, token: str = "", db: AsyncSession = Depends(get_db)):
    """Export conversation as markdown. Auth via query param or header."""
    from fastapi.responses import PlainTextResponse
    from auth import decode_token, get_current_user
    # Try query param auth first (for direct browser links)
    if token:
        payload = decode_token(token)
        user_id = payload["sub"]
    else:
        raise HTTPException(401, "Token required")
    convo = await _get_convo(convo_id, user_id, db)
    result = await db.execute(select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at))
    messages = result.scalars().all()

    md = f"# {convo.title}\n\n"
    md += f"*Exported on {datetime.now().strftime('%B %d, %Y')} | Model: {convo.model}*\n\n---\n\n"
    for m in messages:
        if m.role == "user":
            md += f"## You\n\n{m.content}\n\n"
        elif m.role == "assistant":
            md += f"## Assistant\n\n{m.content}\n\n"
        md += "---\n\n"
    return PlainTextResponse(md, media_type="text/markdown", headers={
        "Content-Disposition": f'attachment; filename="{convo.title[:50].replace(" ", "_")}.md"'
    })


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

        try:
            for round_num in range(max_tool_rounds + 1):
                # Call Ollama
                response_text = ""
                tool_calls = []
                eval_count = 0
                eval_duration = 0

                async with httpx.AsyncClient(timeout=300.0) as client:
                    payload = {
                        "model": req.model,
                        "messages": messages,
                        "stream": True,
                        "options": {"num_ctx": 32768},
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

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # Also parse any inline code blocks as artifacts
        inline_artifacts = _parse_artifacts(full_response)
        for a in inline_artifacts:
            if not any(ea["content"] == a["content"] for ea in all_artifacts):
                all_artifacts.append(a)
        if inline_artifacts:
            yield f"data: {json.dumps({'type': 'artifacts', 'artifacts': inline_artifacts})}\n\n"

        # Save assistant message
        try:
            async with get_db_session() as save_db:
                assistant_msg = Message(
                    conversation_id=convo.id,
                    role="assistant",
                    content=full_response,
                    model=req.model,
                    artifacts=all_artifacts if all_artifacts else None,
                    tool_calls=all_tool_calls if all_tool_calls else None,
                    images=all_images if all_images else None,
                    thinking=all_thinking if all_thinking else None,
                )
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


async def _get_convo(convo_id: str, user_id: str, db: AsyncSession) -> Conversation:
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id, Conversation.user_id == user_id))
    convo = result.scalar_one_or_none()
    if not convo: raise HTTPException(404, "Conversation not found")
    return convo


def _convo_dict(c: Conversation) -> dict:
    return {"id": c.id, "title": c.title, "model": c.model, "project_id": c.project_id, "is_starred": c.is_starred, "created_at": (c.created_at.isoformat() + "Z") if c.created_at else None, "updated_at": (c.updated_at.isoformat() + "Z") if c.updated_at else None}


def _msg_dict(m: Message) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "model": m.model, "artifacts": m.artifacts, "attachments": m.attachments, "images": m.images, "thinking": m.thinking, "tool_calls": m.tool_calls, "tool_results": m.tool_results, "token_count": m.token_count, "created_at": (m.created_at.isoformat() + "Z") if m.created_at else None}


@asynccontextmanager
async def get_db_session():
    async with _async_session() as session:
        yield session
