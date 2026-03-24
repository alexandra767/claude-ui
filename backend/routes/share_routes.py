"""Cross-device sharing — universal clipboard + file drop."""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from models import Base
from auth import get_current_user
from sqlalchemy import Column, String, Text, DateTime, Integer
from datetime import datetime, timezone, timedelta
import os
import uuid
import aiofiles

router = APIRouter(prefix="/api/share", tags=["share"])

SHARE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "shared")
os.makedirs(SHARE_DIR, exist_ok=True)


# ── Model ───────────────────────────────────────────────────────────────────

class SharedItem(Base):
    __tablename__ = "shared_items"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    item_type = Column(String, nullable=False)  # text, image, file, link
    content = Column(Text, default="")  # text content or caption
    filename = Column(String, nullable=True)
    filepath = Column(String, nullable=True)
    file_size = Column(Integer, default=0)
    mime_type = Column(String, default="")
    source_device = Column(String, default="")  # which device sent it
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Routes ──────────────────────────────────────────────────────────────────

class TextShareRequest(BaseModel):
    content: str
    source_device: str = ""


@router.get("/items")
async def list_items(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all shared items, newest first. Auto-cleans items older than 24h."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    # Clean old items
    old = await db.execute(select(SharedItem).where(SharedItem.user_id == user_id, SharedItem.created_at < cutoff))
    for item in old.scalars().all():
        if item.filepath and os.path.exists(item.filepath):
            os.remove(item.filepath)
        await db.delete(item)
    await db.commit()

    # Get current items
    result = await db.execute(
        select(SharedItem).where(SharedItem.user_id == user_id).order_by(desc(SharedItem.created_at))
    )
    items = result.scalars().all()
    return [_item_dict(i) for i in items]


@router.post("/text")
async def share_text(req: TextShareRequest, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Share text/clipboard content."""
    # Detect if it's a URL
    item_type = "link" if req.content.strip().startswith(("http://", "https://")) else "text"
    item = SharedItem(
        user_id=user_id,
        item_type=item_type,
        content=req.content,
        source_device=req.source_device,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _item_dict(item)


@router.post("/file")
async def share_file(
    file: UploadFile = File(...),
    source_device: str = Form(""),
    caption: str = Form(""),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Share a file or image."""
    # Save file
    ext = os.path.splitext(file.filename or "")[1]
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
    filepath = os.path.join(SHARE_DIR, safe_name)

    async with aiofiles.open(filepath, "wb") as f:
        data = await file.read()
        await f.write(data)

    # Determine type
    mime = file.content_type or ""
    if mime.startswith("image/"):
        item_type = "image"
    else:
        item_type = "file"

    item = SharedItem(
        user_id=user_id,
        item_type=item_type,
        content=caption,
        filename=file.filename,
        filepath=filepath,
        file_size=len(data),
        mime_type=mime,
        source_device=source_device,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _item_dict(item)


@router.get("/file/{item_id}")
async def get_file(item_id: str, token: str = "", db: AsyncSession = Depends(get_db)):
    """Download a shared file. Accepts token as query param for img/a tags."""
    from auth import decode_token
    from fastapi import HTTPException
    # Auth via query param (for img src / a href)
    if not token:
        raise HTTPException(401, "Token required")
    payload = decode_token(token)
    user_id = payload["sub"]
    result = await db.execute(select(SharedItem).where(SharedItem.id == item_id, SharedItem.user_id == user_id))
    item = result.scalar_one_or_none()
    if not item or not item.filepath or not os.path.exists(item.filepath):
        raise HTTPException(404, "File not found")
    return FileResponse(item.filepath, filename=item.filename, media_type=item.mime_type or "application/octet-stream")


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SharedItem).where(SharedItem.id == item_id, SharedItem.user_id == user_id))
    item = result.scalar_one_or_none()
    if not item:
        from fastapi import HTTPException
        raise HTTPException(404, "Item not found")
    if item.filepath and os.path.exists(item.filepath):
        os.remove(item.filepath)
    await db.delete(item)
    await db.commit()
    return {"ok": True}


@router.delete("/items")
async def clear_all(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Clear all shared items."""
    result = await db.execute(select(SharedItem).where(SharedItem.user_id == user_id))
    for item in result.scalars().all():
        if item.filepath and os.path.exists(item.filepath):
            os.remove(item.filepath)
        await db.delete(item)
    await db.commit()
    return {"ok": True}


def _item_dict(i: SharedItem) -> dict:
    return {
        "id": i.id,
        "type": i.item_type,
        "content": i.content,
        "filename": i.filename,
        "file_size": i.file_size,
        "mime_type": i.mime_type,
        "source_device": i.source_device,
        "has_file": bool(i.filepath),
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }
