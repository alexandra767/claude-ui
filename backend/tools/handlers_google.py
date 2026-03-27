"""Google service handlers — Gmail, Calendar, Drive, Docs."""
from datetime import datetime, timezone


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
