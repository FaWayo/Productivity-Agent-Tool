import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/notes.db")


def _get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_note(title: str, content: str, tags: str = "") -> dict:
    """
    Save a new note with a title and content.
    Optional: add comma-separated tags (e.g. "work,meeting,q3").
    """
    if not title.strip() or not content.strip():
        return {"error": "Note title and content cannot be empty."}

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
