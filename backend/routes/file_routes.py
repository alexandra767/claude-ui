from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from auth import get_current_user
import os
import aiofiles

router = APIRouter(prefix="/api/files", tags=["files"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    user_dir = os.path.join(UPLOAD_DIR, "chat", user_id)
    os.makedirs(user_dir, exist_ok=True)
    filepath = os.path.join(user_dir, file.filename)
    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)
    return {
        "filename": file.filename,
        "path": filepath,
        "type": file.content_type or "",
        "size": len(content),
    }


@router.get("/read/{filename}")
async def read_file(filename: str, user_id: str = Depends(get_current_user)):
    user_dir = os.path.join(UPLOAD_DIR, "chat", user_id)
    filepath = os.path.join(user_dir, filename)
    # Prevent path traversal
    if not os.path.abspath(filepath).startswith(os.path.abspath(user_dir)):
        raise HTTPException(403, "Access denied")
    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found")
    async with aiofiles.open(filepath, "r", errors="replace") as f:
        content = await f.read()
    return {"filename": filename, "content": content}
