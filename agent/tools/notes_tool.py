import os
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    from notion_client import Client as NotionClient
except Exception:  # pragma: no cover - Notion client may not be installed everywhere
    NotionClient = None

DB_PATH = Path("data/notes.db")


def _get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    )
    conn.commit()
    return conn


def _notion_client():
    """Return a Notion client if configured, else None."""
    if NotionClient is None:
        return None
    token = os.getenv("NOTION_API_TOKEN")
    db_id = os.getenv("NOTION_NOTES_DATABASE_ID")
    if not token or not db_id:
        return None
    return NotionClient(auth=token), db_id


def save_note(title: str, content: str, tags: str = "") -> dict:
    """
    Save a new note with a title and content.
    Optional: add comma-separated tags (e.g. "work,meeting,q3").
    """
    if not title.strip() or not content.strip():
        return {"error": "Note title and content cannot be empty."}

    notion_info = _notion_client()
    if notion_info:
        notion, db_id = notion_info
        tag_values = [t.strip() for t in tags.split(",") if t.strip()]
        try:
            notion.pages.create(
                parent={"database_id": db_id},
                properties={
                    "Title": {"title": [{"text": {"content": title}}]},
                    "Tags": {"multi_select": [{"name": t} for t in tag_values]},
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": content}}],
                        },
                    }
                ],
            )
            return {
                "success": True,
                "title": title,
                "message": f"Note '{title}' saved to Notion.",
            }
        except Exception as e:  # pragma: no cover - network-specific
            return {"error": f"Failed to save note to Notion: {e}"}

    now = datetime.now().isoformat()
    conn = _get_connection()
    cursor = conn.execute(
        "INSERT INTO notes (title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (title, content, tags, now, now),
    )
    conn.commit()
    note_id = cursor.lastrowid
    conn.close()

    return {
        "success": True,
        "id": note_id,
        "title": title,
        "message": f"Note '{title}' saved with ID {note_id}.",
    }


def list_notes(limit: int = 10) -> dict:
    """
    List the most recently saved notes. Returns title, ID, and preview.
    """
    notion_info = _notion_client()
    if notion_info:
        notion, db_id = notion_info
        try:
            resp = notion.databases.query(
                **{"database_id": db_id, "page_size": limit}
            )
            results = []
            for page in resp.get("results", []):
                props = page.get("properties", {})
                title_prop = props.get("Title", {})
                title_parts = title_prop.get("title", []) if title_prop else []
                title = "".join(p.get("plain_text", "") for p in title_parts) or "(no title)"
                tags_prop = props.get("Tags", {})
                tags = ", ".join(t.get("name", "") for t in tags_prop.get("multi_select", []))
                created_at = page.get("created_time", "")
                results.append(
                    {
                        "id": page.get("id"),
                        "title": title,
                        "preview": "(content in Notion)",
                        "tags": tags,
                        "created_at": created_at,
                    }
                )
            if not results:
                return {"count": 0, "notes": [], "message": "No notes saved yet."}
            return {"count": len(results), "notes": results}
        except Exception as e:  # pragma: no cover - network-specific
            return {"error": f"Failed to list notes from Notion: {e}"}

    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, title, content, tags, created_at FROM notes ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    if not rows:
        return {"count": 0, "notes": [], "message": "No notes saved yet."}

    return {
        "count": len(rows),
        "notes": [
            {
                "id": row[0],
                "title": row[1],
                "preview": row[2][:80] + "..." if len(row[2]) > 80 else row[2],
                "tags": row[3],
                "created_at": row[4],
            }
            for row in rows
        ],
    }


def search_notes(keyword: str) -> dict:
    """
    Search notes by keyword in title or content.
    """
    if not keyword.strip():
        return {"error": "Search keyword cannot be empty."}

    notion_info = _notion_client()
    if notion_info:
        notion, db_id = notion_info
        try:
            resp = notion.databases.query(
                **{
                    "database_id": db_id,
                    "filter": {
                        "or": [
                            {
                                "property": "Title",
                                "title": {"contains": keyword},
                            },
                            # Fallback: if you have a Content property, you could also include it here.
                        ]
                    },
                }
            )
            results = []
            for page in resp.get("results", []):
                props = page.get("properties", {})
                title_prop = props.get("Title", {})
                title_parts = title_prop.get("title", []) if title_prop else []
                title = "".join(p.get("plain_text", "") for p in title_parts) or "(no title)"
                tags_prop = props.get("Tags", {})
                tags = ", ".join(t.get("name", "") for t in tags_prop.get("multi_select", []))
                results.append(
                    {
                        "id": page.get("id"),
                        "title": title,
                        "preview": "(content in Notion)",
                        "tags": tags,
                    }
                )
            if not results:
                return {
                    "found": 0,
                    "notes": [],
                    "message": f"No notes found matching '{keyword}'.",
                }
            return {"found": len(results), "keyword": keyword, "notes": results}
        except Exception as e:  # pragma: no cover - network-specific
            return {"error": f"Failed to search notes in Notion: {e}"}

    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, title, content, tags FROM notes WHERE title LIKE ? OR content LIKE ?",
        (f"%{keyword}%", f"%{keyword}%"),
    ).fetchall()
    conn.close()

    if not rows:
        return {
            "found": 0,
            "notes": [],
            "message": f"No notes found matching '{keyword}'.",
        }

    return {
        "found": len(rows),
        "keyword": keyword,
        "notes": [
            {
                "id": row[0],
                "title": row[1],
                "preview": row[2][:120] + "..." if len(row[2]) > 120 else row[2],
                "tags": row[3],
            }
            for row in rows
        ],
    }
