#!/usr/bin/env python3
"""One-time Google Drive/Docs OAuth2 setup."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "google_credentials.json")
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "drive_token.json")

def main():
    print("=== Google Drive/Docs Setup ===")
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"ERROR: {CREDENTIALS_PATH} not found")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=9091, open_browser=False)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    # Test
    drive = build("drive", "v3", credentials=creds)
    results = drive.files().list(pageSize=5, fields="files(id, name)").execute()
    print(f"\nConnected! Found {len(results.get('files', []))} files:")
    for f in results.get("files", []):
        print(f"  {f['name']}")
    print(f"\nToken saved to {TOKEN_PATH}")

if __name__ == "__main__":
    main()
