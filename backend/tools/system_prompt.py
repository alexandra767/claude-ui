"""System prompt template and assembly for chat routes."""

import json
import os
from datetime import datetime


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
- **tutor_topics**: List coding challenge topics (Python, OOP, Data Structures, JS, Swift)
- **tutor_challenge**: Get a coding challenge to solve
- **tutor_validate**: Test the user's code against challenge test cases
- **tutor_validate_dynamic**: Test code against custom test cases you generate (for unlimited challenges)
- **tutor_progress**: Show learning progress and completed challenges
When the user asks for a challenge and you've run out of built-in ones, generate a new challenge yourself with test code and use tutor_validate_dynamic to check their solution.
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
- **security_camera**: View the security camera — captures a live snapshot and describes what it sees (people, vehicles, animals, packages)

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


def _get_persona_prompt(persona_id: str) -> str:
    """Get persona system prompt by ID."""
    try:
        personas_path = os.path.join(os.path.dirname(__file__), "personas.json")
        with open(personas_path) as f:
            personas = json.load(f)
        for p in personas:
            if p["id"] == persona_id:
                return p.get("prompt", "")
    except Exception:
        pass
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


def build_system_prompt(
    location: str,
    timezone: str,
    persona: str | None = None,
    custom_instructions: str | None = None,
    project_system_prompt: str | None = None,
    project_name: str | None = None,
) -> str:
    """Build the full system prompt with optional persona, custom instructions, and project context."""
    system = SYSTEM_PROMPT_TEMPLATE.format(
        location=location,
        timezone=timezone,
        datetime_now=datetime.now().strftime("%A, %B %d, %Y %I:%M %p"),
    )

    if persona:
        persona_prompt = _get_persona_prompt(persona)
        if persona_prompt:
            system += f"\n\nPersona: {persona_prompt}"

    if custom_instructions:
        system += f"\n\nUser's custom instructions: {custom_instructions}"

    if project_system_prompt:
        system += f"\n\nProject instructions: {project_system_prompt}"

    if project_name:
        project_notes = _load_project_notes(project_name)
        if project_notes:
            system += f"\n\nProject knowledge (from saved notes):\n{project_notes}"

    return system
