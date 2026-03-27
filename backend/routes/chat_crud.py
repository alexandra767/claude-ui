from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from models import Conversation, Message
from auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ConversationUpdate(BaseModel):
    title: str | None = None
    is_starred: bool | None = None
    project_id: str | None = None


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_convo(convo_id: str, user_id: str, db: AsyncSession) -> Conversation:
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id, Conversation.user_id == user_id))
    convo = result.scalar_one_or_none()
    if not convo: raise HTTPException(404, "Conversation not found")
    return convo


def _convo_dict(c: Conversation) -> dict:
    return {"id": c.id, "title": c.title, "model": c.model, "project_id": c.project_id, "is_starred": c.is_starred, "created_at": (c.created_at.isoformat() + "Z") if c.created_at else None, "updated_at": (c.updated_at.isoformat() + "Z") if c.updated_at else None}


def _msg_dict(m: Message) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "model": m.model, "artifacts": m.artifacts, "attachments": m.attachments, "images": m.images, "thinking": m.thinking, "tool_calls": m.tool_calls, "tool_results": m.tool_results, "token_count": m.token_count, "created_at": (m.created_at.isoformat() + "Z") if m.created_at else None}


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
    from auth import decode_token
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
