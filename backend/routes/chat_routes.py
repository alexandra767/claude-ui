from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from database import get_db
from models import Conversation, Message, Project
from auth import get_current_user
from datetime import datetime, timezone
import httpx
import json
import re

router = APIRouter(prefix="/api/chat", tags=["chat"])

OLLAMA_BASE = "http://localhost:11434"

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code and return the output. Use this for calculations, data processing, or any code execution task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "language": {"type": "string", "enum": ["python", "javascript", "bash"], "default": "python"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information on a given query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_artifact",
            "description": "Create a rich artifact like a document, code file, SVG, HTML page, or React component for the user to view.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique artifact identifier"},
                    "type": {"type": "string", "enum": ["code", "document", "html", "svg", "react", "mermaid"], "description": "Artifact type"},
                    "title": {"type": "string", "description": "Artifact title"},
                    "content": {"type": "string", "description": "Artifact content"},
                    "language": {"type": "string", "description": "Programming language (for code type)"},
                },
                "required": ["id", "type", "title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of an uploaded file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the file to read"},
                },
                "required": ["filename"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are Claude, a helpful AI assistant. You have access to several tools:

1. **execute_code** - Run Python/JavaScript/Bash code. Use this for calculations, data analysis, or demonstrations.
2. **web_search** - Search the web for current information.
3. **create_artifact** - Create rich content (code files, documents, HTML pages, SVG graphics, React components, Mermaid diagrams) that will be displayed in a side panel.
4. **read_file** - Read uploaded files.

When creating artifacts, use the create_artifact tool. Artifacts are for substantial, standalone content that the user might want to reference, copy, or iterate on. Use artifacts for:
- Code files or scripts (type: "code", include language)
- Documents or reports (type: "document")
- HTML pages or interactive demos (type: "html")
- SVG graphics (type: "svg")
- React components (type: "react")
- Mermaid diagrams (type: "mermaid")

For short code snippets in explanations, use regular markdown code blocks instead.

Always be helpful, thorough, and accurate. Format your responses with clear markdown."""


class SendMessageRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    model: str = "qwen3.5:122b"
    project_id: str | None = None
    attachments: list[dict] | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    is_starred: bool | None = None
    project_id: str | None = None


@router.get("/conversations")
async def list_conversations(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
    )
    convos = result.scalars().all()
    return [_convo_dict(c) for c in convos]


@router.get("/conversations/{convo_id}")
async def get_conversation(
    convo_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convo = await _get_convo(convo_id, user_id, db)
    result = await db.execute(
        select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at)
    )
    messages = result.scalars().all()
    d = _convo_dict(convo)
    d["messages"] = [_msg_dict(m) for m in messages]
    return d


@router.put("/conversations/{convo_id}")
async def update_conversation(
    convo_id: str,
    req: ConversationUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convo = await _get_convo(convo_id, user_id, db)
    if req.title is not None:
        convo.title = req.title
    if req.is_starred is not None:
        convo.is_starred = req.is_starred
    if req.project_id is not None:
        convo.project_id = req.project_id if req.project_id else None
    await db.commit()
    await db.refresh(convo)
    return _convo_dict(convo)


@router.delete("/conversations/{convo_id}")
async def delete_conversation(
    convo_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convo = await _get_convo(convo_id, user_id, db)
    await db.delete(convo)
    await db.commit()
    return {"ok": True}


@router.post("/send")
async def send_message(
    req: SendMessageRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get or create conversation
    if req.conversation_id:
        convo = await _get_convo(req.conversation_id, user_id, db)
    else:
        convo = Conversation(user_id=user_id, model=req.model, project_id=req.project_id)
        db.add(convo)
        await db.commit()
        await db.refresh(convo)

    # Save user message
    user_msg = Message(
        conversation_id=convo.id,
        role="user",
        content=req.message,
        attachments=req.attachments,
    )
    db.add(user_msg)
    await db.commit()

    # Build message history
    result = await db.execute(
        select(Message).where(Message.conversation_id == convo.id).order_by(Message.created_at)
    )
    all_msgs = result.scalars().all()

    # Build system prompt
    system = SYSTEM_PROMPT
    if req.project_id:
        proj_result = await db.execute(select(Project).where(Project.id == req.project_id))
        project = proj_result.scalar_one_or_none()
        if project and project.system_prompt:
            system += f"\n\nProject instructions: {project.system_prompt}"

    messages = [{"role": "system", "content": system}]
    for m in all_msgs:
        msg_entry = {"role": m.role, "content": m.content}
        messages.append(msg_entry)

    convo.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Stream response from Ollama
    async def generate():
        full_response = ""
        artifacts = []
        tool_calls_data = []

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_BASE}/api/chat",
                    json={
                        "model": req.model,
                        "messages": messages,
                        "stream": True,
                        "options": {"num_ctx": 32768},
                    },
                ) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                full_response += chunk
                                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                            if data.get("done"):
                                eval_count = data.get("eval_count", 0)
                                yield f"data: {json.dumps({'type': 'metrics', 'eval_count': eval_count, 'eval_duration': data.get('eval_duration', 0)})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # Parse artifacts from response
        artifacts = _parse_artifacts(full_response)
        if artifacts:
            yield f"data: {json.dumps({'type': 'artifacts', 'artifacts': artifacts})}\n\n"

        # Save assistant message
        async with get_db_session() as save_db:
            assistant_msg = Message(
                conversation_id=convo.id,
                role="assistant",
                content=full_response,
                model=req.model,
                artifacts=artifacts if artifacts else None,
            )
            save_db.add(assistant_msg)

            # Auto-title on first message
            if len(all_msgs) <= 1:
                title = _generate_title(req.message)
                stmt = select(Conversation).where(Conversation.id == convo.id)
                result = await save_db.execute(stmt)
                c = result.scalar_one()
                c.title = title
            await save_db.commit()

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


def _parse_artifacts(text: str) -> list[dict]:
    """Extract artifact-like code blocks from the response."""
    artifacts = []
    # Match code blocks with language tags
    pattern = r'```(\w+)\n(.*?)```'
    matches = re.finditer(pattern, text, re.DOTALL)
    for i, match in enumerate(matches):
        lang = match.group(1)
        content = match.group(2).strip()
        # Only create artifacts for substantial code blocks (>5 lines)
        if content.count('\n') >= 5:
            artifact_type = "code"
            if lang in ("html", "htm"):
                artifact_type = "html"
            elif lang == "svg":
                artifact_type = "svg"
            elif lang == "mermaid":
                artifact_type = "mermaid"
            artifacts.append({
                "id": f"artifact-{i}",
                "type": artifact_type,
                "title": f"{lang.title()} code",
                "content": content,
                "language": lang,
            })
    return artifacts


def _generate_title(message: str) -> str:
    """Generate a short title from the first user message."""
    title = message.strip()[:80]
    if len(message) > 80:
        title = title.rsplit(" ", 1)[0] + "..."
    return title


async def _get_convo(convo_id: str, user_id: str, db: AsyncSession) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == convo_id, Conversation.user_id == user_id)
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    return convo


def _convo_dict(c: Conversation) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "model": c.model,
        "project_id": c.project_id,
        "is_starred": c.is_starred,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _msg_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "model": m.model,
        "artifacts": m.artifacts,
        "attachments": m.attachments,
        "tool_calls": m.tool_calls,
        "tool_results": m.tool_results,
        "token_count": m.token_count,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# Helper for saving from streaming context
from database import async_session as _async_session
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session():
    async with _async_session() as session:
        yield session
