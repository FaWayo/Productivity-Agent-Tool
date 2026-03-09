import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

CALENDAR_FILE = Path("data/calendar.json")


def _load_calendar() -> dict:
    if CALENDAR_FILE.exists():
        return json.loads(CALENDAR_FILE.read_text())
    return {"events": []}


def _save_calendar(data: dict):
    CALENDAR_FILE.write_text(json.dumps(data, indent=2))


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
    calendar = _load_calendar()
    events = [e for e in calendar["events"] if e["date"] == date_str]

    for event in events:
        # Simple overlap check
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
