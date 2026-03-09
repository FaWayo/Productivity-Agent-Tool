from datetime import date

from agent.tools.calendar_tool import get_calendar_events, check_availability, create_calendar_event
from agent.tools.email_tool import search_emails, read_email, draft_email, send_email
from agent.tools.notes_tool import save_note, list_notes, search_notes
from agent.tools.search_tool import web_search

print("=== CALENDAR TOOLS ===")
print("get_calendar_events(today):", get_calendar_events(date.today().isoformat()))
print("check_availability(today, 09:00-10:00):",
      check_availability(date.today().isoformat(), "09:00", "10:00"))
print("create_calendar_event demo:",
      create_calendar_event("Demo Meeting", date.today().isoformat(),
                            "15:00", "16:00", "Zoom", ["alice@example.com"]))

print("\n=== EMAIL TOOLS ===")
print("search_emails by sender 'Sarah':", search_emails(from_sender="Sarah"))
print("search_emails by subject 'meeting':", search_emails(subject_keyword="meeting"))

email_search = search_emails(limit=1)
if email_search["emails"]:
    first_id = email_search["emails"][0]["id"]
    print("read_email(first result):", read_email(first_id))
else:
    print("read_email: skipped (no emails in data/email.json)")

print("draft_email demo:",
      draft_email("test@example.com", "Hello", "Just a quick check-in."))
print("send_email demo:",
      send_email("test@example.com", "Hello", "Just a quick check-in."))

print("\n=== NOTES TOOLS ===")
print("save_note demo:",
      save_note("Test Note", "This is a test note from the tool check.", "demo,tools"))
print("list_notes demo:", list_notes(limit=3))
print("search_notes for 'test':", search_notes("test"))

print("\n=== WEB SEARCH TOOL ===")
print("web_search demo:",
      web_search("best jollof rice in Accra", max_results=2))