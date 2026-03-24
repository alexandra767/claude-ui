#!/usr/bin/env python3
"""Manual Drive/Docs auth — paste the redirect URL after authorizing."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
CREDS_PATH = os.path.join(os.path.dirname(__file__), 'google_credentials_drive.json')
TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'drive_token.json')

flow = Flow.from_client_secrets_file(CREDS_PATH, scopes=SCOPES, redirect_uri='http://localhost:9098/')

auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
print("\n1. Open this URL in a PRIVATE Firefox window:")
print(f"\n{auth_url}\n")
print("2. After authorizing, Firefox will go to a page that says 'Unable to connect'")
print("   That's OK! Copy the ENTIRE URL from the Firefox address bar")
print("   It will look like: http://localhost:9098/?state=...&code=...&scope=...")
print("\n3. Paste that URL here:")

redirect_url = input("\n> ").strip()
flow.fetch_token(authorization_response=redirect_url)

with open(TOKEN_PATH, 'w') as f:
    f.write(flow.credentials.to_json())

print("\nToken saved! Testing...")
drive = build('drive', 'v3', credentials=flow.credentials)
results = drive.files().list(pageSize=3, fields='files(id, name)').execute()
print(f"Connected! {len(results.get('files', []))} files:")
for f in results.get('files', []):
    print(f"  {f['name']}")
