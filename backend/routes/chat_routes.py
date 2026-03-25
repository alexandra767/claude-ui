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

# Location: prefer browser GPS, fall back to IP geolocation
_location_cache: dict = {}

async def _update_location_from_gps(lat: float, lon: float):
    """Reverse geocode GPS coordinates to city name."""
    global _location_cache
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
                headers={"User-Agent": "ClaudeUI/1.0"},
            )
            data = resp.json()
            addr = data.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county", "Unknown")
            state = addr.get("state", "")
            _location_cache = {
                "location": f"{city}, {state}" if state else city,
                "timezone": "America/New_York",  # Could detect from coords but this covers most US
                "lat": lat,
                "lon": lon,
                "source": "gps",
            }
    except Exception:
        _location_cache = {"location": f"{lat},{lon}", "timezone": "America/New_York", "source": "gps"}


async def _get_user_location() -> tuple[str, str]:
    """Returns (location_string, timezone). Prefers GPS, falls back to home base."""
    global _location_cache
    if _location_cache:
        return _location_cache["location"], _location_cache["timezone"]
    # Default: Ridgway, PA (home base — IP geolocation is unreliable on Starlink)
    _location_cache = {
        "location": "Ridgway, PA",
        "timezone": "America/New_York",
        "lat": 41.4203,
        "lon": -78.7286,
        "source": "default",
    }
    return "Ridgway, PA", "America/New_York"

# ── Tool Definitions (sent to Ollama) ───────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute code and return output. Use for calculations, data processing, scripts, or demonstrations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to execute"},
                    "language": {"type": "string", "enum": ["python", "javascript", "bash"], "default": "python", "description": "Programming language"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, facts, or anything you don't know.",
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
            "name": "fetch_url",
            "description": "Fetch and read the content of a webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "Timezone name (optional)", "default": "local"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a mathematical expression. Supports all Python math functions (sin, cos, sqrt, log, pi, e, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate, e.g. 'sqrt(144) + pi'"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_search",
            "description": "Search Gmail emails. Use Gmail search syntax like 'from:user@example.com', 'subject:hello', 'is:unread', 'newer_than:2d'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query"},
                    "max_results": {"type": "integer", "description": "Max emails to return", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_read",
            "description": "Read the full content of a specific email by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Email message ID"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_send",
            "description": "Send an email or reply to an existing email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body text"},
                    "reply_to_id": {"type": "string", "description": "Message ID to reply to (optional)"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_list",
            "description": "List upcoming Google Calendar events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Number of days to look ahead", "default": 7},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_create",
            "description": "Create a new Google Calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time in ISO 8601 format (e.g. 2026-03-25T10:00:00)"},
                    "end_time": {"type": "string", "description": "End time in ISO 8601 format"},
                    "description": {"type": "string", "description": "Event description"},
                    "location": {"type": "string", "description": "Event location"},
                    "timezone": {"type": "string", "description": "Timezone", "default": "America/New_York"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee email addresses"},
                },
                "required": ["summary", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_artifact",
            "description": "Create a rich artifact (code file, document, HTML page, SVG, diagram) displayed in a side panel for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique artifact ID"},
                    "type": {"type": "string", "enum": ["code", "document", "html", "svg", "react", "mermaid"]},
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
            "name": "generate_image",
            "description": "Generate an image from a text description using AI (Gemini). Returns the file path of the generated image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Detailed description of the image to generate"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_image",
            "description": "Edit an existing image with AI. Provide the file path and describe the changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Full file path to the image to edit"},
                    "prompt": {"type": "string", "description": "Description of changes to make to the image"},
                },
                "required": ["image_path", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codebase_tree",
            "description": "View the file and directory structure of a local project. Use this to understand a project's layout before reading specific files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the project directory, e.g. ~/WANDERLINK or ~/claude-ui"},
                    "max_depth": {"type": "integer", "description": "How deep to scan (default 3)", "default": 3},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codebase_read",
            "description": "Read the contents of a specific file from a local project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the file to read, e.g. ~/WANDERLINK/Wanderlink/Services/WeatherService.swift"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codebase_search",
            "description": "Search for text/code across all files in a local project directory. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the project directory to search"},
                    "query": {"type": "string", "description": "Text to search for (case-insensitive)"},
                    "max_results": {"type": "integer", "description": "Max results to return", "default": 20},
                },
                "required": ["path", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_transcript",
            "description": "Get the transcript/captions from a YouTube video. Use this to summarize, analyze, or answer questions about YouTube videos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "YouTube video URL or video ID"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a note or memory that persists across conversations. Also saves to Google Drive. Use this when the user asks you to remember something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content (markdown supported)"},
                    "category": {"type": "string", "description": "Category (general, todo, reminder, preference)", "default": "general"},
                    "project": {"type": "string", "description": "Project name for organizing (e.g. 'GigLedger', 'WanderLink'). Creates a subfolder."},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "Read the full content of a saved note. Use list_notes first to find the filename.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The note filename (e.g. 'GigLedger Project Overview.md')"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_note",
            "description": "Append new content to an existing note without losing existing data. Use list_notes first to find the filename.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The note filename (e.g. 'GigLedger Project Overview.md')"},
                    "content": {"type": "string", "description": "New content to append to the note"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "List and search saved notes/memories from previous conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search query to filter notes"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_list_files",
            "description": "List recent files in Google Drive, optionally filtered by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional filename search query"},
                    "max_results": {"type": "integer", "description": "Max files to return", "default": 15},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_search",
            "description": "Search Google Drive files by content (full-text search).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query to find in file contents"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_read_doc",
            "description": "Read the text content of a Google Doc by its document ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Google Doc document ID"},
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_create_doc",
            "description": "Create a new Google Doc with a title and content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Document text content"},
                },
                "required": ["title", "content"],
            },
        },
    },
]

SYSTEM_PROMPT_TEMPLATE = """You are a helpful AI assistant with access to powerful tools. Use them whenever they would help answer the user's question.

The user is located in {location} (timezone: {timezone}). When they ask about weather, time, or local info, use this location automatically — do not ask them where they are.

Available tools:
- **execute_code**: Run Python, JavaScript, or Bash code
- **web_search**: Search the web for current information
- **fetch_url**: Read a webpage's content
- **get_datetime**: Get current date and time
- **get_weather**: Get weather for any location
- **calculator**: Evaluate math expressions
- **gmail_search**: Search the user's Gmail (supports Gmail search syntax)
- **gmail_read**: Read a specific email by ID
- **gmail_send**: Send or reply to emails
- **calendar_list**: List upcoming Google Calendar events
- **calendar_create**: Create calendar events
- **create_artifact**: Create rich content (code, HTML, SVG, docs) shown in a side panel
- **generate_image**: Generate images from text descriptions using AI (Gemini)
- **edit_image**: Edit/modify existing images with AI
- **codebase_tree**: View the file structure of a local project directory
- **codebase_read**: Read any file from a local project
- **codebase_search**: Search for text across all files in a project
- **youtube_transcript**: Get transcript/captions from a YouTube video for summarization
- **save_note**: Save a new note/memory that persists across conversations
- **read_note**: Read the full content of a saved note
- **update_note**: Append to an existing note without losing data
- **list_notes**: List and search saved notes
- **drive_list_files**: List recent files in Google Drive
- **drive_search**: Search Google Drive by content
- **drive_read_doc**: Read a Google Doc's text content
- **drive_create_doc**: Create a new Google Doc

Guidelines:
- Use tools proactively — don't just describe what you could do, actually do it
- When the user asks "what do you know about X" or "tell me about X" — ALWAYS check list_notes first before searching the web. Your notes contain information from previous conversations.
- When the user says "remember X" or "save this" — use save_note to persist it
- When the user says "update my note about X" — use list_notes to find it, then update_note to append
- For math, use the calculator tool instead of computing in your head
- For current events, dates, weather — use the appropriate tool
- For code demonstrations, use execute_code to actually run it and show output
- For local projects on the Spark, use codebase_tree/codebase_read/codebase_search to explore them
- Create artifacts for substantial standalone content the user might want to keep
- For short inline code examples, use regular markdown code blocks
- Always format responses with clear markdown

Current date/time: {datetime_now}"""


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
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
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

    # System prompt
    location, tz = await _get_user_location()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        location=location,
        timezone=tz,
        datetime_now=datetime.now().strftime("%A, %B %d, %Y %I:%M %p"),
    )
    # Add custom instructions from user profile
    user_result = await db.execute(select(User).where(User.id == user_id))
    user_obj = user_result.scalar_one_or_none()
    if user_obj and user_obj.custom_instructions:
        system += f"\n\nUser's custom instructions: {user_obj.custom_instructions}"

    if req.project_id:
        proj_result = await db.execute(select(Project).where(Project.id == req.project_id))
        project = proj_result.scalar_one_or_none()
        if project:
            if project.system_prompt:
                system += f"\n\nProject instructions: {project.system_prompt}"
            # Auto-load all notes for this project
            project_notes = _load_project_notes(project.name)
            if project_notes:
                system += f"\n\nProject knowledge (from saved notes):\n{project_notes}"

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
                        img_b64 = _resize_image_for_vision(filepath)
                        if img_b64:
                            msg_images.append(img_b64)
                else:
                    # Text/PDF attachments → read content
                    file_text = _read_file_content(filepath, filename)
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
                    if tool_name in ("generate_image", "edit_image") and tool_result.get("success") and tool_result.get("filename"):
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

def _resize_image_for_vision(filepath: str, max_size: int = 1024) -> str:
    """Resize image and convert to base64 for vision model. Keeps under ~1MB."""
    import base64
    from io import BytesIO
    try:
        from PIL import Image
        img = Image.open(filepath)
        # Convert RGBA to RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        # Resize if too large
        w, h = img.size
        if w > max_size or h > max_size:
            ratio = min(max_size / w, max_size / h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        # Save to buffer as JPEG (smaller than PNG)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception:
        # Fallback: read raw file
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            if len(data) > 5 * 1024 * 1024:  # Skip files over 5MB
                return ""
            return base64.b64encode(data).decode('utf-8')
        except Exception:
            return ""


def _load_project_notes(project_name: str) -> str:
    """Load all notes for a project and return as combined text."""
    notes_dir = os.path.expanduser("~/claude-ui/notes")
    combined = ""

    # Check project subfolder
    project_dir = os.path.join(notes_dir, project_name)
    if os.path.isdir(project_dir):
        for f in sorted(os.listdir(project_dir)):
            if f.endswith(".md"):
                filepath = os.path.join(project_dir, f)
                with open(filepath, "r") as fh:
                    content = fh.read()
                combined += f"\n--- {f} ---\n{content}\n"

    # Also check root notes dir for notes matching project name
    for f in sorted(os.listdir(notes_dir)):
        if f.endswith(".md") and project_name.lower() in f.lower():
            filepath = os.path.join(notes_dir, f)
            with open(filepath, "r") as fh:
                content = fh.read()
            combined += f"\n--- {f} ---\n{content}\n"

    # Truncate if too long (keep under 10k chars to leave room for conversation)
    if len(combined) > 10000:
        combined = combined[:10000] + "\n\n...(notes truncated)"

    return combined.strip()


def _read_file_content(filepath: str, filename: str) -> str:
    """Read file content, supporting PDF, text, code, and common formats."""
    import os
    if not filepath or not os.path.exists(filepath):
        return ""
    try:
        ext = os.path.splitext(filename.lower())[1]
        # PDF
        if ext == ".pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            # Truncate very long PDFs
            if len(text) > 15000:
                text = text[:15000] + "\n\n...(truncated, showing first ~15000 characters)"
            return text
        # Binary files we can't read
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".mp4", ".zip", ".tar", ".gz"):
            return f"[Binary file: {filename}, {os.path.getsize(filepath)} bytes]"
        # Everything else: try as text
        with open(filepath, "r", errors="replace") as f:
            text = f.read()
        if len(text) > 15000:
            text = text[:15000] + "\n\n...(truncated)"
        return text
    except Exception as e:
        return f"[Could not read file: {e}]"


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
    return {"id": c.id, "title": c.title, "model": c.model, "project_id": c.project_id, "is_starred": c.is_starred, "created_at": c.created_at.isoformat() if c.created_at else None, "updated_at": c.updated_at.isoformat() if c.updated_at else None}


def _msg_dict(m: Message) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "model": m.model, "artifacts": m.artifacts, "attachments": m.attachments, "images": m.images, "thinking": m.thinking, "tool_calls": m.tool_calls, "tool_results": m.tool_results, "token_count": m.token_count, "created_at": m.created_at.isoformat() if m.created_at else None}


@asynccontextmanager
async def get_db_session():
    async with _async_session() as session:
        yield session
