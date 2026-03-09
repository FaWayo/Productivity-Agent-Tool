import json
from pathlib import Path
from typing import Optional

EMAILS_FILE = Path("data/email.json")


def _load_emails() -> dict:
    if EMAILS_FILE.exists():
        return json.loads(EMAILS_FILE.read_text())
    return {"emails": []}


def search_emails(
    from_sender: str = "", subject_keyword: str = "", limit: int = 5
) -> dict:
    """
    Search emails by sender name/email or subject keyword.
    Returns a list of matching emails (without full body for brevity).
    """
    inbox = _load_emails()
    emails = inbox["emails"]

    if from_sender:
        emails = [
            e
            for e in emails
            if from_sender.lower() in e["from"].lower()
            or from_sender.lower() in e["from_name"].lower()
        ]
    if subject_keyword:
        emails = [e for e in emails if subject_keyword.lower() in e["subject"].lower()]

    emails = emails[:limit]

    if not emails:
        return {"found": 0, "emails": [], "message": "No emails matched your search."}

    return {
        "found": len(emails),
        "emails": [
            {
                "id": e["id"],
                "from": e["from_name"],
                "email": e["from"],
                "subject": e["subject"],
                "date": e["date"],
                "preview": e["body"][:80] + "..." if len(e["body"]) > 80 else e["body"],
            }
            for e in emails
        ],
    }


def read_email(email_id: str) -> dict:
    """
    Get the full content of an email by its ID.
    """
    inbox = _load_emails()
    for email in inbox["emails"]:
        if email["id"] == email_id:
            return {
                "id": email["id"],
                "from": email["from_name"],
                "email": email["from"],
                "subject": email["subject"],
                "date": email["date"],
                "body": email["body"],
            }
    return {"error": f"Email with ID '{email_id}' not found."}


def draft_email(to: str, subject: str, body: str) -> dict:
    """
    Draft an email reply. This does NOT send — it returns the draft
    for human review and approval before sending.
    IMPORTANT: Always call this before send_email.
    """
    return {
        "draft": True,
        "to": to,
        "subject": subject,
        "body": body,
        "status": "PENDING_APPROVAL",
        "message": "Email drafted. Awaiting user approval to send.",
    }


def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send an email. This action is irreversible.
    MUST only be called after the user has approved the draft.
    """
    # In a real app, this calls Gmail API. Here we simulate it.
    return {
        "success": True,
        "to": to,
        "subject": subject,
        "message": f"Email sent to {to} with subject '{subject}'.",
    }
