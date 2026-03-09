import base64
import email
import json
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover - Google libs may not be installed in all envs
    Request = Credentials = InstalledAppFlow = build = None

EMAILS_FILE = Path("data/email.json")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _load_emails() -> dict:
    if EMAILS_FILE.exists():
        return json.loads(EMAILS_FILE.read_text())
    return {"emails": []}


def _gmail_service():
    """Return a Gmail API service client if credentials are configured, else None."""
    if build is None or Credentials is None or InstalledAppFlow is None:
        return None

    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "google_gmail_token.json")
    if not creds_path or not Path(creds_path).exists():
        return None

    token_file = Path(token_path)
    creds: Optional[Credentials] = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def search_emails(
    from_sender: str = "", subject_keyword: str = "", limit: int = 5
) -> dict:
    """
    Search emails by sender name/email or subject keyword.
    Returns a list of matching emails (without full body for brevity).
    """
    service = _gmail_service()
    if service:
        query_parts = []
        if from_sender:
            query_parts.append(f'from:{from_sender}')
        if subject_keyword:
            query_parts.append(f'subject:{subject_keyword}')
        query = " ".join(query_parts) if query_parts else ""

        resp = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=limit)
            .execute()
        )
        messages = resp.get("messages", [])
        if not messages:
            return {"found": 0, "emails": [], "message": "No emails matched your search."}

        results = []
        for m in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
                .execute()
            )
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            from_header = headers.get("From", "")
            subject = headers.get("Subject", "(no subject)")
            date_val = headers.get("Date", "")
            results.append(
                {
                    "id": msg["id"],
                    "from": from_header,
                    "email": from_header,
                    "subject": subject,
                    "date": date_val,
                    "preview": subject,
                }
            )

        return {"found": len(results), "emails": results}

    # Fallback: local JSON inbox
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
    service = _gmail_service()
    if service:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=email_id, format="full")
                .execute()
            )
        except Exception as e:  # pragma: no cover - network-specific
            return {"error": f"Failed to read email from Gmail: {e}"}

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        from_header = headers.get("From", "")
        subject = headers.get("Subject", "(no subject)")
        date_val = headers.get("Date", "")

        # Decode plain text body if present
        body_text = ""
        parts = msg.get("payload", {}).get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    body_text = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")
                    break

        return {
            "id": msg["id"],
            "from": from_header,
            "email": from_header,
            "subject": subject,
            "date": date_val,
            "body": body_text or "(no plain-text body)",
        }

    # Fallback: local JSON inbox
    inbox = _load_emails()
    for email_obj in inbox["emails"]:
        if email_obj["id"] == email_id:
            return {
                "id": email_obj["id"],
                "from": email_obj["from_name"],
                "email": email_obj["from"],
                "subject": email_obj["subject"],
                "date": email_obj["date"],
                "body": email_obj["body"],
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
    service = _gmail_service()
    if service:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        try:
            sent = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            return {
                "success": True,
                "to": to,
                "subject": subject,
                "message": f"Email sent to {to} with subject '{subject}'.",
                "id": sent.get("id"),
            }
        except Exception as e:  # pragma: no cover - network-specific
            return {"error": f"Failed to send email via Gmail: {e}"}

    # Fallback: simulate send
    return {
        "success": True,
        "to": to,
        "subject": subject,
        "message": f"Email sent to {to} with subject '{subject}'.",
    }
