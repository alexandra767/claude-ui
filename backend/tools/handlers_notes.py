"""Notes/memory handlers — save, read, update, list notes."""
import os
from datetime import datetime


# ── Notes / Memory ──────────────────────────────────────────────────────────

NOTES_DIR = os.path.expanduser("~/claude-ui/notes")
os.makedirs(NOTES_DIR, exist_ok=True)


async def _save_note(args: dict) -> dict:
    """Save a note/memory locally and to Google Drive."""
    title = args.get("title", "untitled")
    content = args.get("content", "")
    category = args.get("category", "general")
    project = args.get("project", "")

    # Sanitize filename
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
    filename = f"{safe_title}.md"

    # Save locally (in project subfolder if specified)
    if project:
        safe_project = "".join(c for c in project if c.isalnum() or c in " -_").strip()
        local_dir = os.path.join(NOTES_DIR, safe_project)
        os.makedirs(local_dir, exist_ok=True)
    else:
        local_dir = NOTES_DIR
    filepath = os.path.join(local_dir, filename)

    full_content = f"# {title}\n\n*Category: {category} | Saved: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n{content}"
    with open(filepath, "w") as f:
        f.write(full_content)

    # Also save to Google Drive
    drive_link = ""
    try:
        drive_link = _save_note_to_drive(title, full_content, project)
    except Exception:
        pass

    result = {"saved": True, "title": title, "filename": filename, "category": category, "local_path": filepath}
    if drive_link:
        result["google_doc_link"] = drive_link
    return result


def _save_note_to_drive(title: str, content: str, project: str = "") -> str:
    """Save or update note in Google Drive. Finds existing doc by title, or creates new one."""
    from tools.google_auth import get_drive_service, get_docs_service

    drive = get_drive_service()
    docs = get_docs_service()
    if not drive or not docs:
        return ""

    # Find or create "Claude UI Notes" folder
    root_folder_id = _get_or_create_folder(drive, "Claude UI Notes", parent_id=None)

    # If project specified, create subfolder
    if project:
        folder_id = _get_or_create_folder(drive, project, parent_id=root_folder_id)
    else:
        folder_id = root_folder_id

    # Check if doc already exists with this title in this folder
    existing = drive.files().list(
        q=f"name='{title}' and '{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false",
        fields="files(id)",
    ).execute()

    if existing.get("files"):
        # Update existing doc — clear content and rewrite
        doc_id = existing["files"][0]["id"]
        doc = docs.documents().get(documentId=doc_id).execute()
        # Get document length to clear it
        end_index = doc.get("body", {}).get("content", [{}])[-1].get("endIndex", 1)
        requests = []
        if end_index > 2:
            requests.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}})
        requests.append({"insertText": {"location": {"index": 1}, "text": content}})
        docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    else:
        # Create new doc
        doc = docs.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        # Move to correct folder
        drive.files().update(
            fileId=doc_id, addParents=folder_id, removeParents="root", fields="id",
        ).execute()
        if content:
            requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
            docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"


def _get_or_create_folder(drive, name: str, parent_id: str | None) -> str:
    """Find existing folder or create new one in Google Drive."""
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    results = drive.files().list(q=q, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    # Create folder
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]
    folder = drive.files().create(body=body, fields="id").execute()
    return folder["id"]


async def _read_note(args: dict) -> dict:
    """Read the full content of a saved note."""
    filename = args.get("filename", "")
    if not filename:
        return {"error": "filename is required (use list_notes to find it)"}
    filepath = os.path.join(NOTES_DIR, filename)
    if not os.path.exists(filepath):
        return {"error": f"Note not found: {filename}"}
    with open(filepath, "r") as f:
        content = f.read()
    return {"filename": filename, "content": content}


async def _update_note(args: dict) -> dict:
    """Append content to an existing note without losing data."""
    filename = args.get("filename", "")
    content_to_add = args.get("content", "")

    if not filename:
        return {"error": "filename is required (use list_notes to find it)"}

    # Search in main dir and subdirectories
    filepath = os.path.join(NOTES_DIR, filename)
    if not os.path.exists(filepath):
        # Check subdirectories
        for subdir in os.listdir(NOTES_DIR):
            check = os.path.join(NOTES_DIR, subdir, filename)
            if os.path.exists(check):
                filepath = check
                break
        else:
            return {"error": f"Note not found: {filename}"}

    with open(filepath, "r") as f:
        existing = f.read()

    with open(filepath, "w") as f:
        f.write(existing.rstrip())
        f.write(f"\n\n---\n*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(content_to_add)

    return {"updated": True, "filename": filename}


async def _list_notes(args: dict) -> dict:
    """List all saved notes, optionally filtered by search query."""
    query = args.get("query", "").lower()
    notes = []

    # Walk notes dir and subdirectories
    for root, dirs, files in os.walk(NOTES_DIR):
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            filepath = os.path.join(root, f)
            with open(filepath, "r") as fh:
                content = fh.read()
            if query and query not in content.lower() and query not in f.lower():
                continue
            title = content.split("\n")[0].lstrip("# ").strip() if content else f
            rel_dir = os.path.relpath(root, NOTES_DIR)
            project = rel_dir if rel_dir != "." else ""
            notes.append({
                "title": title,
                "filename": f,
                "project": project,
                "preview": content[content.find("\n\n") + 2:][:200] if "\n\n" in content else content[:200],
            })
    return {"notes": notes, "count": len(notes)}
