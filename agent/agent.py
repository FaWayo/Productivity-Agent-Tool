import os
from datetime import date

from dotenv import load_dotenv
from pydantic_ai import Agent

from .system_prompt import SYSTEM_PROMPT
from .tools.calendar_tool import (
    check_availability,
    create_calendar_event,
    get_calendar_events,
)
from .tools.email_tool import draft_email, read_email, search_emails, send_email
from .tools.notes_tool import list_notes, save_note, search_notes
from .tools.search_tool import web_search

load_dotenv()

# Format system prompt with today's date
system_prompt = SYSTEM_PROMPT.format(
    today_date=date.today().isoformat(), user_name="User"
)

# Create the agent. We rely on PydanticAI's Google integration, configured
agent = Agent(
    model="google-gla:gemini-2.5-flash",
    system_prompt=system_prompt,
)


# Register all tools with the agent
@agent.tool_plain
def tool_get_calendar_events(date_str: str) -> dict:
    """Get all calendar events for a given date (YYYY-MM-DD format)."""
    return get_calendar_events(date_str)


@agent.tool_plain
def tool_check_availability(date_str: str, start_time: str, end_time: str) -> dict:
    """Check if a time slot is free. Times in HH:MM format."""
    return check_availability(date_str, start_time, end_time)


@agent.tool_plain
def tool_create_calendar_event(
    title: str,
    date_str: str,
    start_time: str,
    end_time: str,
    location: str = "",
    attendees: list[str] = [],
) -> dict:
    """Create a new calendar event. Requires user approval first."""
    return create_calendar_event(
        title, date_str, start_time, end_time, location, attendees
    )


@agent.tool_plain
def tool_search_emails(
    from_sender: str = "", subject_keyword: str = "", limit: int = 5
) -> dict:
    """Search emails by sender or subject keyword."""
    return search_emails(from_sender, subject_keyword, limit)


@agent.tool_plain
def tool_read_email(email_id: str) -> dict:
    """Read the full content of an email by its ID."""
    return read_email(email_id)


@agent.tool_plain
def tool_draft_email(to: str, subject: str, body: str) -> dict:
    """Draft an email reply. Does not send — stages for approval."""
    return draft_email(to, subject, body)


@agent.tool_plain
def tool_send_email(to: str, subject: str, body: str) -> dict:
    """Send an email. Only call after explicit user approval."""
    return send_email(to, subject, body)


@agent.tool_plain
def tool_web_search(query: str, max_results: int = 3) -> dict:
    """Search the web for current information."""
    return web_search(query, max_results)


@agent.tool_plain
def tool_save_note(title: str, content: str, tags: str = "") -> dict:
    """Save a note to persistent storage."""
    return save_note(title, content, tags)


@agent.tool_plain
def tool_list_notes(limit: int = 10) -> dict:
    """List recently saved notes."""
    return list_notes(limit)


@agent.tool_plain
def tool_search_notes(keyword: str) -> dict:
    """Search notes by keyword in title or content."""
    return search_notes(keyword)
