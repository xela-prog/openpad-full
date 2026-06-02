#!/usr/bin/env python3
"""
Run this once in your terminal to authorize openpad with Google Calendar.
It will open a browser for OAuth, then save ~/.openpad/token.pickle.
After that, the calendar view inside openpad will work automatically.

Usage:
    python auth_calendar.py
"""

from pathlib import Path
import pickle

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_FILE = Path.home() / ".openpad" / "token.pickle"
CREDS_FILE = Path.home() / ".openpad" / "credentials.json"

def main():
    if not CREDS_FILE.exists():
        print(f"ERROR: credentials.json not found at {CREDS_FILE}")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        return

    print(f"Found credentials.json at {CREDS_FILE}")

    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
        if creds and creds.valid:
            print(f"token.pickle already exists and is valid at {TOKEN_FILE}")
            print("You're good to go — open openpad and the calendar should work.")
            return
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            print("Token expired, refreshing...")
            creds.refresh(Request())
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
            print(f"Token refreshed and saved to {TOKEN_FILE}")
            return

    print("Starting OAuth flow — your browser will open...")
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)

    print(f"\nSuccess! token.pickle saved to {TOKEN_FILE}")
    print("Open openpad — the calendar will now load your events.")

if __name__ == "__main__":
    main()
