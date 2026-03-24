"""Google OAuth2 authentication for Gmail and Calendar."""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOOLS_DIR = os.path.dirname(__file__)
GMAIL_TOKEN_PATH = os.path.join(TOOLS_DIR, "gmail_token.json")
CALENDAR_TOKEN_PATH = os.path.join(TOOLS_DIR, "calendar_token.json")

_gmail_service = None
_calendar_service = None


def _load_creds(token_path: str, scopes: list[str]) -> Credentials | None:
    if not os.path.exists(token_path):
        return None
    creds = Credentials.from_authorized_user_file(token_path, scopes)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except Exception:
            return None
    if not creds.valid:
        return None
    return creds


def get_gmail_service():
    global _gmail_service
    if _gmail_service:
        return _gmail_service
    creds = _load_creds(GMAIL_TOKEN_PATH, [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ])
    if not creds:
        return None
    _gmail_service = build("gmail", "v1", credentials=creds)
    return _gmail_service


def get_calendar_service():
    global _calendar_service
    if _calendar_service:
        return _calendar_service
    creds = _load_creds(CALENDAR_TOKEN_PATH, [
        "https://www.googleapis.com/auth/calendar",
    ])
    if not creds:
        return None
    _calendar_service = build("calendar", "v3", credentials=creds)
    return _calendar_service


def is_google_connected() -> bool:
    return os.path.exists(GMAIL_TOKEN_PATH) or os.path.exists(CALENDAR_TOKEN_PATH)
