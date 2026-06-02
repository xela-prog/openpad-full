import os
import pickle
from pathlib import Path
from datetime import datetime, timedelta, timezone

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_FILE = Path.home() / ".openpad" / "token.pickle"
CREDS_FILE = Path.home() / ".openpad" / "credentials.json"


def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        from google.auth.transport.requests import Request
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return creds


def get_events_for_month(year: int, month: int) -> dict:
    """Return dict of day -> list of events for the given month."""
    try:
        from googleapiclient.discovery import build
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        # Month boundaries
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # Get all calendars
        calendars = service.calendarList().list().execute()
        result_items = []
        for cal in calendars.get("items", []):
            try:
                cal_result = service.events().list(
                    calendarId=cal["id"],
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=200,
                ).execute()
                result_items.extend(cal_result.get("items", []))
            except Exception:
                continue

        events_by_day = {}
        for event in result_items:
            start_raw = event["start"].get("dateTime", event["start"].get("date", ""))
            if "T" in start_raw:
                dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                day = dt.day
                end_raw = event["end"].get("dateTime", "")
                if end_raw:
                    end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                    time_str = f"{dt.strftime('%I:%M %p').lstrip('0')} → {end_dt.strftime('%I:%M %p').lstrip('0')}"
                else:
                    time_str = dt.strftime("%I:%M %p").lstrip("0")
            else:
                dt = datetime.strptime(start_raw, "%Y-%m-%d")
                day = dt.day
                time_str = "All day"

            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append({
                "title": event.get("summary", "No title"),
                "time": time_str,
                "color": _classify_event(event.get("summary", "")),
            })
        return events_by_day
    except Exception as e:
        return {"error": str(e)}


def get_events_for_day(year: int, month: int, day: int) -> list:
    """Return list of events for a specific day."""
    events_by_day = get_events_for_month(year, month)
    if "error" in events_by_day:
        return []
    return events_by_day.get(day, [])


def _classify_event(title: str) -> str:
    """Return event type based on title keywords."""
    title_lower = title.lower()
    exam_keywords = ["exam", "test", "midterm", "final", "quiz", "deadline", "due"]
    for kw in exam_keywords:
        if kw in title_lower:
            return "exam"
    return "event"
