#!/usr/bin/env python3
"""
One-time Google OAuth2 setup.

STEPS:
1. Go to https://console.cloud.google.com/
2. Create a project (or use existing)
3. Enable Gmail API and Google Calendar API
4. Go to Credentials → Create OAuth 2.0 Client ID → Desktop App
5. Download the JSON and save it as:
   ~/claude-ui/backend/tools/google_credentials.json
6. Run this script: python3 ~/claude-ui/backend/tools/google_setup.py
7. Follow the browser link to authorize
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))

from google_auth import _get_credentials, get_gmail_service, get_calendar_service, CREDENTIALS_PATH

def main():
    print("=" * 50)
    print("  Google Account Setup for Claude UI")
    print("=" * 50)
    print()

    if not os.path.exists(CREDENTIALS_PATH):
        print(f"ERROR: Credentials file not found at:")
        print(f"  {CREDENTIALS_PATH}")
        print()
        print("To set this up:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project (or use existing)")
        print("3. Enable 'Gmail API' and 'Google Calendar API'")
        print("4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID")
        print("5. Choose 'Desktop app' as application type")
        print("6. Download the JSON file")
        print(f"7. Save it as: {CREDENTIALS_PATH}")
        print("8. Run this script again")
        return

    print("Found credentials file. Starting authorization...")
    print("A browser window will open (or a URL will be printed).")
    print("Log in with your Google account and grant access.")
    print()

    creds = _get_credentials()
    if not creds:
        print("Authorization failed.")
        return

    print()
    print("Testing Gmail...")
    gmail = get_gmail_service()
    if gmail:
        profile = gmail.users().getProfile(userId="me").execute()
        print(f"  Connected as: {profile.get('emailAddress')}")
        print(f"  Total messages: {profile.get('messagesTotal')}")
    else:
        print("  Gmail connection failed")

    print()
    print("Testing Calendar...")
    cal = get_calendar_service()
    if cal:
        calendars = cal.calendarList().list().execute()
        for c in calendars.get("items", [])[:5]:
            print(f"  Calendar: {c.get('summary')}")
    else:
        print("  Calendar connection failed")

    print()
    print("Setup complete! Your AI can now access Gmail and Calendar.")


if __name__ == "__main__":
    main()
