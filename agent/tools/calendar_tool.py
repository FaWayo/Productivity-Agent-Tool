import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover - Google libs may not be installed in all envs
    Request = Credentials = InstalledAppFlow = build = None


CALENDAR_FILE = Path("data/calendar.json")
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _load_calendar() -> dict:
    if CALENDAR_FILE.exists():
        return json.loads(CALENDAR_FILE.read_text())
    return {"events": []}


def _save_calendar(data: dict):
    CALENDAR_FILE.write_text(json.dumps(data, indent=2))


def _google_calendar_service():
    """Return a Google Calendar service client if credentials are configured, else None."""
    if build is None or Credentials is None or InstalledAppFlow is None:
        return None

    creds_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH")
    token_path = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "google_calendar_token.json")
    if not creds_path or not Path(creds_path).exists():
        return None

    token_file = Path(token_path)
    creds: Optional[Credentials] = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), GOOGLE_CALENDAR_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, GOOGLE_CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_calendar_events(date_str: str) -> dict:
    """
    Get all calendar events for a specific date.
    date_str format: YYYY-MM-DD. Use today's date if user says 'today'.
    """
    try:
        # Validate date format
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

    # Prefer Google Calendar if configured
    service = _google_calendar_service()
    if service:
        day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start = day.isoformat()
        end = (day + timedelta(days=1) - timedelta(seconds=1)).isoformat()
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])

        if not items:
            return {
                "date": date_str,
                "events": [],
                "message": "No events found for this date.",
            }

        def _fmt(ev: dict) -> dict:
            start_info = ev.get("start", {})
            end_info = ev.get("end", {})
            start_time = start_info.get("dateTime") or start_info.get("date") or ""
            end_time = end_info.get("dateTime") or end_info.get("date") or ""
            return {
                "title": ev.get("summary", "(no title)"),
                "time": f"{start_time} - {end_time}",
                "location": ev.get("location", "No location"),
                "attendees": [a.get("email") for a in ev.get("attendees", [])],
            }

        return {
            "date": date_str,
            "count": len(items),
            "events": [_fmt(e) for e in items],
        }

    # Fallback to local JSON calendar
    calendar = _load_calendar()
    events = [e for e in calendar["events"] if e["date"] == date_str]

    if not events:
        return {
            "date": date_str,
            "events": [],
            "message": "No events found for this date.",
        }

    return {
        "date": date_str,
        "count": len(events),
        "events": [
            {
                "title": e["title"],
                "time": f"{e['start_time']} - {e['end_time']}",
                "location": e.get("location", "No location"),
                "attendees": e.get("attendees", []),
            }
            for e in events
        ],
    }


def check_availability(date_str: str, start_time: str, end_time: str) -> dict:
    """
    Check if a time slot is free on the calendar.
    date_str: YYYY-MM-DD, start_time and end_time: HH:MM
    """
    service = _google_calendar_service()
    if service:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

        start_dt = datetime.combine(day, datetime.strptime(start_time, "%H:%M").time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(day, datetime.strptime(end_time, "%H:%M").time(), tzinfo=timezone.utc)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
        if items:
            ev = items[0]
            return {
                "available": False,
                "conflict": f"'{ev.get('summary', '(no title)')}' conflicts with this time slot.",
            }

        return {
            "available": True,
            "message": f"Time slot {start_time}-{end_time} on {date_str} is free.",
        }

    # Fallback: local JSON calendar
    calendar = _load_calendar()
    events = [e for e in calendar["events"] if e["date"] == date_str]

    for event in events:
        if not (end_time <= event["start_time"] or start_time >= event["end_time"]):
            return {
                "available": False,
                "conflict": f"'{event['title']}' is scheduled from {event['start_time']} to {event['end_time']}",
            }

    return {
        "available": True,
        "message": f"Time slot {start_time}-{end_time} on {date_str} is free.",
    }


def create_calendar_event(
    title: str,
    date_str: str,
    start_time: str,
    end_time: str,
    location: str = "",
    attendees: list[str] = [],
) -> dict:
    """
    Create a new calendar event. Returns the created event details.
    Requires human approval before calling — the UI handles this.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

    service = _google_calendar_service()
    if service:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_dt = datetime.combine(day, datetime.strptime(start_time, "%H:%M").time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(day, datetime.strptime(end_time, "%H:%M").time(), tzinfo=timezone.utc)

        event_body = {
            "summary": title,
            "location": location,
            "attendees": [{"email": a} for a in attendees],
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }

        created = service.events().insert(calendarId="primary", body=event_body).execute()
        return {
            "success": True,
            "message": f"Event '{title}' created on {date_str} at {start_time}.",
            "event": {
                "id": created.get("id"),
                "title": created.get("summary", title),
                "date": date_str,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "attendees": attendees,
            },
        }

    # Fallback: local JSON calendar
    calendar = _load_calendar()
    new_event = {
        "id": f"evt_{len(calendar['events']) + 1:03d}",
        "title": title,
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "attendees": attendees,
    }
    calendar["events"].append(new_event)
    _save_calendar(calendar)

    return {
        "success": True,
        "message": f"Event '{title}' created on {date_str} at {start_time}.",
        "event": new_event,
    }
