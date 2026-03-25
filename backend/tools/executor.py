"""Central tool executor — routes tool calls to the right handler."""
import json
import subprocess
import tempfile
import os
import re
import math
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup


async def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool by name and return the result."""
    # Check if it's an MCP tool (prefixed with mcp__)
    if name.startswith("mcp__"):
        return _call_mcp_tool(name, arguments)

    handlers = {
        "execute_code": _execute_code,
        "web_search": _web_search,
        "fetch_url": _fetch_url,
        "get_datetime": _get_datetime,
        "get_weather": _get_weather,
        "calculator": _calculator,
        "create_artifact": _create_artifact,
        "generate_image": _generate_image,
        "edit_image": _edit_image,
        "gmail_search": _gmail_search,
        "gmail_read": _gmail_read,
        "gmail_send": _gmail_send,
        "calendar_list": _calendar_list,
        "calendar_create": _calendar_create,
        "drive_search": _drive_search,
        "drive_read_doc": _drive_read_doc,
        "drive_create_doc": _drive_create_doc,
        "save_note": _save_note,
        "list_notes": _list_notes,
        "youtube_transcript": _youtube_transcript,
        "drive_list_files": _drive_list_files,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await handler(arguments)
    except Exception as e:
        return {"error": f"{name} failed: {str(e)}"}


# ── Code Execution ──────────────────────────────────────────────────────────

async def _execute_code(args: dict) -> dict:
    code = args.get("code", "")
    language = args.get("language", "python")

    if language == "python":
        return _run_subprocess(["python3", "-c", code])
    elif language == "javascript":
        return _run_subprocess(["node", "-e", code])
    elif language == "bash":
        return _run_subprocess(["bash", "-c", code])
    return {"error": f"Unsupported language: {language}"}


def _run_subprocess(cmd: list[str]) -> dict:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        return {"output": output.strip(), "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"output": "Execution timed out (30s limit)", "exit_code": -1}


# ── Web Search ──────────────────────────────────────────────────────────────

async def _web_search(args: dict) -> dict:
    query = args.get("query", "")
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result"):
            title_el = r.select_one(".result__a")
            snippet_el = r.select_one(".result__snippet")
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })
            if len(results) >= 8:
                break
        return {"results": results}


# ── Fetch URL ───────────────────────────────────────────────────────────────

async def _fetch_url(args: dict) -> dict:
    url = args.get("url", "")
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script/style
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Truncate to ~4000 chars
        if len(text) > 4000:
            text = text[:4000] + "\n...(truncated)"
        title = soup.title.string if soup.title else ""
        return {"title": title, "content": text}


# ── Date/Time ───────────────────────────────────────────────────────────────

async def _get_datetime(args: dict) -> dict:
    tz_name = args.get("timezone", "local")
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%A, %B %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "timezone": tz_name,
        "unix": int(now.timestamp()),
    }


# ── Weather (Open-Meteo, free, no API key, GPS-based) ───────────────────────

# Ridgway, PA default coords
DEFAULT_LAT = 41.4203
DEFAULT_LON = -78.7286

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


async def _get_weather(args: dict) -> dict:
    location = args.get("location", "")
    lat = args.get("lat")
    lon = args.get("lon")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # If a city name is given but no coords, geocode it
        if location and not lat:
            try:
                geo_resp = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": location, "count": 1, "language": "en"},
                )
                geo_data = geo_resp.json()
                results = geo_data.get("results", [])
                if results:
                    lat = results[0]["latitude"]
                    lon = results[0]["longitude"]
                    location = f"{results[0].get('name', location)}, {results[0].get('admin1', '')}"
            except Exception:
                pass

        # Fall back to cached GPS location from browser, then default
        if not lat:
            try:
                from routes.chat_routes import _location_cache
                if _location_cache.get("lat"):
                    lat = _location_cache["lat"]
                    lon = _location_cache["lon"]
                    location = _location_cache.get("location", "Your location")
            except Exception:
                pass

        if not lat:
            lat = DEFAULT_LAT
            lon = DEFAULT_LON
            location = location or "Ridgway, PA"

        # Reverse geocode if we have coords but no name
        if not location:
            try:
                rgeo = await client.get(
                    "https://api.bigdatacloud.net/data/reverse-geocode-client",
                    params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
                )
                rgeo_data = rgeo.json()
                city = rgeo_data.get("city") or rgeo_data.get("locality") or rgeo_data.get("principalSubdivision", "")
                state = rgeo_data.get("principalSubdivision", "")
                location = f"{city}, {state}" if state and state != city else city or f"{lat:.2f}, {lon:.2f}"
            except Exception:
                location = f"{lat:.2f}, {lon:.2f}"

        # Fetch weather from Open-Meteo
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
        )
        resp = await client.get(url)
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})
        weather_code = current.get("weather_code", 0)

        return {
            "location": location,
            "temperature_f": round(current.get("temperature_2m", 0)),
            "feels_like_f": round(current.get("apparent_temperature", 0)),
            "condition": WEATHER_CODES.get(weather_code, "Unknown"),
            "humidity": current.get("relative_humidity_2m", ""),
            "wind_mph": round(current.get("wind_speed_10m", 0)),
            "high_f": round(daily.get("temperature_2m_max", [0])[0]),
            "low_f": round(daily.get("temperature_2m_min", [0])[0]),
            "sunrise": daily.get("sunrise", [""])[0].split("T")[-1] if daily.get("sunrise") else "",
            "sunset": daily.get("sunset", [""])[0].split("T")[-1] if daily.get("sunset") else "",
        }


# ── Calculator ──────────────────────────────────────────────────────────────

async def _calculator(args: dict) -> dict:
    expression = args.get("expression", "")
    # Safe math evaluation
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("_")
    }
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"expression": expression, "result": str(result)}
    except Exception as e:
        return {"expression": expression, "error": str(e)}


# ── Artifact Creation ───────────────────────────────────────────────────────

async def _create_artifact(args: dict) -> dict:
    return {
        "artifact_created": True,
        "id": args.get("id", ""),
        "type": args.get("type", "code"),
        "title": args.get("title", "Untitled"),
    }


# ── Gmail ───────────────────────────────────────────────────────────────────

async def _gmail_search(args: dict) -> dict:
    from tools.google_auth import get_gmail_service
    service = get_gmail_service()
    if not service:
        return {"error": "Gmail not connected. Run the setup: python3 backend/tools/google_setup.py"}

    query = args.get("query", "")
    max_results = args.get("max_results", 10)
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = []
    for msg_ref in results.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        messages.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })
    return {"emails": messages, "count": len(messages)}


async def _gmail_read(args: dict) -> dict:
    from tools.google_auth import get_gmail_service
    service = get_gmail_service()
    if not service:
        return {"error": "Gmail not connected. Run the setup: python3 backend/tools/google_setup.py"}

    msg_id = args.get("id", "")
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

    # Extract body
    body = ""
    payload = msg.get("payload", {})
    if "body" in payload and payload["body"].get("data"):
        import base64
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                import base64
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break

    # Truncate long emails
    if len(body) > 3000:
        body = body[:3000] + "\n...(truncated)"

    return {
        "id": msg_id,
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "body": body,
    }


async def _gmail_send(args: dict) -> dict:
    from tools.google_auth import get_gmail_service
    service = get_gmail_service()
    if not service:
        return {"error": "Gmail not connected. Run the setup: python3 backend/tools/google_setup.py"}

    import base64
    from email.mime.text import MIMEText

    to = args.get("to", "")
    subject = args.get("subject", "")
    body = args.get("body", "")
    reply_to_id = args.get("reply_to_id")

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    if reply_to_id:
        # Get original message for threading
        original = service.users().messages().get(userId="me", id=reply_to_id, format="metadata",
            metadataHeaders=["Message-ID", "Subject"]).execute()
        orig_headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        message["In-Reply-To"] = orig_headers.get("Message-ID", "")
        message["References"] = orig_headers.get("Message-ID", "")
        thread_id = original.get("threadId")
    else:
        thread_id = None

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body_payload = {"raw": raw}
    if thread_id:
        body_payload["threadId"] = thread_id

    sent = service.users().messages().send(userId="me", body=body_payload).execute()
    return {"sent": True, "message_id": sent.get("id", ""), "to": to, "subject": subject}


# ── Google Calendar ─────────────────────────────────────────────────────────

async def _calendar_list(args: dict) -> dict:
    from tools.google_auth import get_calendar_service
    service = get_calendar_service()
    if not service:
        return {"error": "Google Calendar not connected. Run the setup: python3 backend/tools/google_setup.py"}

    from datetime import timedelta
    days_ahead = args.get("days_ahead", 7)
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=days_ahead)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=time_max.isoformat(),
        maxResults=20,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for event in events_result.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})
        events.append({
            "id": event.get("id"),
            "summary": event.get("summary", "(no title)"),
            "start": start.get("dateTime", start.get("date", "")),
            "end": end.get("dateTime", end.get("date", "")),
            "location": event.get("location", ""),
            "description": (event.get("description", "") or "")[:200],
        })
    return {"events": events, "count": len(events), "period": f"next {days_ahead} days"}


async def _calendar_create(args: dict) -> dict:
    from tools.google_auth import get_calendar_service
    service = get_calendar_service()
    if not service:
        return {"error": "Google Calendar not connected. Run the setup: python3 backend/tools/google_setup.py"}

    event_body = {
        "summary": args.get("summary", ""),
        "description": args.get("description", ""),
        "start": {"dateTime": args.get("start_time"), "timeZone": args.get("timezone", "America/New_York")},
        "end": {"dateTime": args.get("end_time"), "timeZone": args.get("timezone", "America/New_York")},
    }
    if args.get("location"):
        event_body["location"] = args["location"]
    if args.get("attendees"):
        event_body["attendees"] = [{"email": e} for e in args["attendees"]]

    event = service.events().insert(calendarId="primary", body=event_body).execute()
    return {
        "created": True,
        "id": event.get("id"),
        "summary": event.get("summary"),
        "link": event.get("htmlLink", ""),
    }


# ── YouTube Transcript ──────────────────────────────────────────────────────

async def _youtube_transcript(args: dict) -> dict:
    """Get transcript/captions from a YouTube video."""
    from youtube_transcript_api import YouTubeTranscriptApi
    import re as _re

    url = args.get("url", "")
    # Extract video ID from various URL formats
    video_id = ""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for p in patterns:
        m = _re.search(p, url)
        if m:
            video_id = m.group(1)
            break

    if not video_id:
        return {"error": f"Could not extract video ID from: {url}"}

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)

        # Combine all text segments
        full_text = ""
        for segment in transcript.snippets:
            full_text += segment.text + " "

        full_text = full_text.strip()

        # Truncate if very long
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n\n...(truncated)"

        return {
            "video_id": video_id,
            "transcript": full_text,
            "word_count": len(full_text.split()),
            "url": f"https://youtube.com/watch?v={video_id}",
        }
    except Exception as e:
        return {"error": f"Could not get transcript: {str(e)}. The video may not have captions available."}


# ── Notes / Memory ──────────────────────────────────────────────────────────

NOTES_DIR = os.path.expanduser("~/claude-ui/notes")
os.makedirs(NOTES_DIR, exist_ok=True)


async def _save_note(args: dict) -> dict:
    """Save a note/memory. Notes persist across conversations."""
    title = args.get("title", "untitled")
    content = args.get("content", "")
    category = args.get("category", "general")

    # Sanitize filename
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
    filename = f"{safe_title}.md"
    filepath = os.path.join(NOTES_DIR, filename)

    with open(filepath, "w") as f:
        f.write(f"# {title}\n\n")
        f.write(f"*Category: {category} | Saved: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(content)

    return {"saved": True, "title": title, "filename": filename, "category": category}


async def _list_notes(args: dict) -> dict:
    """List all saved notes, optionally filtered by search query."""
    query = args.get("query", "").lower()
    notes = []
    for f in sorted(os.listdir(NOTES_DIR)):
        if not f.endswith(".md"):
            continue
        filepath = os.path.join(NOTES_DIR, f)
        with open(filepath, "r") as fh:
            content = fh.read()
        if query and query not in content.lower() and query not in f.lower():
            continue
        # Extract title from first line
        title = content.split("\n")[0].lstrip("# ").strip() if content else f
        notes.append({
            "title": title,
            "filename": f,
            "preview": content[content.find("\n\n") + 2:][:200] if "\n\n" in content else content[:200],
        })
    return {"notes": notes, "count": len(notes)}


# ── Google Drive / Docs ─────────────────────────────────────────────────────

async def _drive_list_files(args: dict) -> dict:
    from tools.google_auth import get_drive_service
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not connected. Run: python3 backend/tools/google_docs_setup.py"}
    query = args.get("query", "")
    max_results = args.get("max_results", 15)
    q_parts = ["trashed=false"]
    if query:
        q_parts.append(f"name contains '{query}'")
    results = service.files().list(
        q=" and ".join(q_parts),
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, webViewLink, size)",
        orderBy="modifiedTime desc",
    ).execute()
    files = []
    for f in results.get("files", []):
        files.append({
            "id": f["id"],
            "name": f["name"],
            "type": f.get("mimeType", ""),
            "modified": f.get("modifiedTime", ""),
            "link": f.get("webViewLink", ""),
            "size": f.get("size", ""),
        })
    return {"files": files, "count": len(files)}


async def _drive_search(args: dict) -> dict:
    from tools.google_auth import get_drive_service
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not connected. Run: python3 backend/tools/google_docs_setup.py"}
    query = args.get("query", "")
    results = service.files().list(
        q=f"fullText contains '{query}' and trashed=false",
        pageSize=10,
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        orderBy="modifiedTime desc",
    ).execute()
    files = [{"id": f["id"], "name": f["name"], "type": f.get("mimeType", ""), "link": f.get("webViewLink", "")} for f in results.get("files", [])]
    return {"files": files, "count": len(files), "query": query}


async def _drive_read_doc(args: dict) -> dict:
    from tools.google_auth import get_docs_service, get_drive_service
    doc_id = args.get("document_id", "")
    if not doc_id:
        return {"error": "document_id is required"}

    # Try Google Docs first
    docs_service = get_docs_service()
    if docs_service:
        try:
            doc = docs_service.documents().get(documentId=doc_id).execute()
            # Extract text content
            content = ""
            for element in doc.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for el in element["paragraph"].get("elements", []):
                        if "textRun" in el:
                            content += el["textRun"].get("content", "")
            title = doc.get("title", "")
            if len(content) > 10000:
                content = content[:10000] + "\n\n...(truncated)"
            return {"title": title, "content": content, "document_id": doc_id}
        except Exception:
            pass

    # Fallback: try downloading as plain text via Drive
    drive_service = get_drive_service()
    if not drive_service:
        return {"error": "Google Drive not connected. Run: python3 backend/tools/google_docs_setup.py"}
    try:
        import io
        from googleapiclient.http import MediaIoBaseDownload
        request = drive_service.files().export_media(fileId=doc_id, mimeType="text/plain")
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        content = buf.getvalue().decode("utf-8", errors="replace")
        if len(content) > 10000:
            content = content[:10000] + "\n\n...(truncated)"
        return {"content": content, "document_id": doc_id}
    except Exception as e:
        return {"error": str(e)}


async def _drive_create_doc(args: dict) -> dict:
    from tools.google_auth import get_docs_service
    service = get_docs_service()
    if not service:
        return {"error": "Google Docs not connected. Run: python3 backend/tools/google_docs_setup.py"}

    title = args.get("title", "Untitled")
    content = args.get("content", "")

    # Create the doc
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # Add content
    if content:
        requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
        service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

    return {
        "created": True,
        "document_id": doc_id,
        "title": title,
        "link": f"https://docs.google.com/document/d/{doc_id}/edit",
    }


# ── Image Generation (nano-banana via MCP) ──────────────────────────────────

def _call_mcp_tool(name: str, arguments: dict) -> dict:
    """Route mcp__<server>__<tool> calls to the MCP client."""
    from tools.mcp_client import call_mcp_tool
    parts = name.split("__", 2)  # mcp__server__tool
    if len(parts) != 3:
        return {"error": f"Invalid MCP tool name: {name}"}
    _, server, tool = parts
    result = call_mcp_tool(server.replace("_", "-"), tool, arguments, timeout=120)
    # Extract text content from MCP response
    if isinstance(result, dict) and "content" in result:
        contents = result["content"]
        if isinstance(contents, list):
            texts = [c.get("text", "") for c in contents if c.get("type") == "text"]
            return {"result": "\n".join(texts) if texts else str(contents)}
    return result


async def _generate_image(args: dict) -> dict:
    """Generate an image using Imagen 4.0 Ultra (Google's best image model)."""
    from google import genai
    import uuid as _uuid

    prompt = args.get("prompt", "")
    api_key = os.environ.get("GEMINI_API_KEY", "")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_images(
            model="imagen-4.0-ultra-generate-001",
            prompt=prompt,
        )

        if response.generated_images:
            output_dir = os.path.expanduser("~/generated_imgs")
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{_uuid.uuid4().hex[:12]}.png"
            output_path = os.path.join(output_dir, filename)

            img_bytes = response.generated_images[0].image.image_bytes
            with open(output_path, "wb") as f:
                f.write(img_bytes)

            return {
                "success": True,
                "file_path": output_path,
                "filename": filename,
                "prompt": prompt,
                "message": f"Image generated and saved to {output_path}",
            }

        return {"success": False, "error": "No image generated"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _edit_image(args: dict) -> dict:
    """Edit an existing image using Gemini API."""
    from google import genai
    from google.genai import types
    import base64 as b64
    import uuid as _uuid

    image_path = args.get("image_path", "")
    prompt = args.get("prompt", "")
    api_key = os.environ.get("GEMINI_API_KEY", "")

    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image not found: {image_path}"}

    try:
        client = genai.Client(api_key=api_key)

        with open(image_path, "rb") as f:
            img_data = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[
                types.Content(parts=[
                    types.Part.from_bytes(data=img_data, mime_type="image/png"),
                    types.Part.from_text(text=prompt),
                ])
            ],
        )

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
                    output_dir = os.path.expanduser("~/generated_imgs")
                    os.makedirs(output_dir, exist_ok=True)
                    filename = f"{_uuid.uuid4().hex[:12]}_edited.png"
                    output_path = os.path.join(output_dir, filename)

                    img_bytes = part.inline_data.data
                    if isinstance(img_bytes, str):
                        img_bytes = b64.b64decode(img_bytes)
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)

                    return {"success": True, "file_path": output_path, "filename": filename, "prompt": prompt, "message": f"Image edited and saved to {output_path}"}

        return {"success": False, "error": "No image in response"}
    except Exception as e:
        return {"success": False, "error": str(e)}
