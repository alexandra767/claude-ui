from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from models import Project, ProjectFile, Conversation
from auth import get_current_user
import os
import aiofiles

router = APIRouter(prefix="/api/projects", tags=["projects"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    color: str = "#DA7756"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    color: str | None = None


@router.get("/")
async def list_projects(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.user_id == user_id).order_by(Project.updated_at.desc()))
    projects = result.scalars().all()
    out = []
    for p in projects:
        d = _proj_dict(p)
        convo_count = await db.execute(select(Conversation).where(Conversation.project_id == p.id))
        d["conversation_count"] = len(convo_count.scalars().all())
        out.append(d)
    return out


@router.post("/")
async def create_project(req: ProjectCreate, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = Project(user_id=user_id, name=req.name, description=req.description, system_prompt=req.system_prompt, color=req.color)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _proj_dict(project)


@router.get("/{project_id}")
async def get_project(project_id: str, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, user_id, db)
    d = _proj_dict(project)
    # Get conversations
    result = await db.execute(select(Conversation).where(Conversation.project_id == project_id).order_by(Conversation.updated_at.desc()))
    d["conversations"] = [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in result.scalars().all()]
    # Get files
    result = await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id))
    d["files"] = [{"id": f.id, "filename": f.filename, "file_type": f.file_type, "file_size": f.file_size} for f in result.scalars().all()]
    return d


@router.put("/{project_id}")
async def update_project(project_id: str, req: ProjectUpdate, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, user_id, db)
    for field in ("name", "description", "system_prompt", "color"):
        val = getattr(req, field)
        if val is not None:
            setattr(project, field, val)
    await db.commit()
    await db.refresh(project)
    return _proj_dict(project)


@router.delete("/{project_id}")
async def delete_project(project_id: str, user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, user_id, db)
    await db.delete(project)
    await db.commit()
    return {"ok": True}


@router.post("/{project_id}/files")
async def upload_project_file(project_id: str, file: UploadFile = File(...), user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, user_id, db)
    proj_dir = os.path.join(UPLOAD_DIR, "projects", project_id)
    os.makedirs(proj_dir, exist_ok=True)
    filepath = os.path.join(proj_dir, file.filename)
    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)
    pf = ProjectFile(project_id=project_id, filename=file.filename, filepath=filepath, file_type=file.content_type or "", file_size=len(content))
    db.add(pf)
    await db.commit()
    await db.refresh(pf)
    return {"id": pf.id, "filename": pf.filename, "file_size": pf.file_size}


async def _get_project(project_id: str, user_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


def _proj_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "system_prompt": p.system_prompt,
        "color": p.color,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
