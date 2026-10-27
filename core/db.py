import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS content_ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    format TEXT NOT NULL,
    title TEXT NOT NULL,
    script_text TEXT NOT NULL,
    scenes_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    telegram_message_id INTEGER,
    video_status TEXT,
    video_path TEXT,
    video_telegram_message_id INTEGER,
    video_error TEXT
);
"""

# Columns added after the initial release — kept separate from SCHEMA so
# existing databases can be migrated with ALTER TABLE instead of losing data.
_MIGRATION_COLUMNS = {
    "video_status": "TEXT",
    "video_path": "TEXT",
    "video_telegram_message_id": "INTEGER",
    "video_error": "TEXT",
}

VIDEO_STATUSES = ("processing", "ready", "approved", "rejected", "failed")


@dataclass(frozen=True)
class ContentIdea:
    id: int
    created_at: str
    format: str
    title: str
    script_text: str
    scenes: list
    status: str
    telegram_message_id: Optional[int]
    video_status: Optional[str]
    video_path: Optional[str]
    video_telegram_message_id: Optional[int]
    video_error: Optional[str]

    @staticmethod
    def from_row(row: sqlite3.Row) -> "ContentIdea":
        return ContentIdea(
            id=row["id"],
            created_at=row["created_at"],
            format=row["format"],
            title=row["title"],
            script_text=row["script_text"],
            scenes=json.loads(row["scenes_json"]),
            status=row["status"],
            telegram_message_id=row["telegram_message_id"],
            video_status=row["video_status"],
            video_path=row["video_path"],
            video_telegram_message_id=row["video_telegram_message_id"],
            video_error=row["video_error"],
        )


@contextmanager
def _connect(db_path: str):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(SCHEMA)
        existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(content_ideas)")}
        for column, column_type in _MIGRATION_COLUMNS.items():
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE content_ideas ADD COLUMN {column} {column_type}")


def create_idea(db_path: str, format: str, title: str, script_text: str, scenes: list) -> int:
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO content_ideas (created_at, format, title, script_text, scenes_json, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (datetime.now(timezone.utc).isoformat(), format, title, script_text, json.dumps(scenes, ensure_ascii=False)),
        )
        return cursor.lastrowid


def set_telegram_message_id(db_path: str, idea_id: int, telegram_message_id: int) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE content_ideas SET telegram_message_id = ? WHERE id = ?",
            (telegram_message_id, idea_id),
        )


def update_status(db_path: str, idea_id: int, status: str) -> None:
    if status not in ("pending", "approved", "rejected"):
        raise ValueError(f"Invalid status: {status}")
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE content_ideas SET status = ? WHERE id = ?",
            (status, idea_id),
        )


def get_by_id(db_path: str, idea_id: int) -> Optional[ContentIdea]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM content_ideas WHERE id = ?", (idea_id,)
        ).fetchone()
        return ContentIdea.from_row(row) if row else None


def get_by_telegram_message_id(db_path: str, telegram_message_id: int) -> Optional[ContentIdea]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM content_ideas WHERE telegram_message_id = ?", (telegram_message_id,)
        ).fetchone()
        return ContentIdea.from_row(row) if row else None


def get_approved(db_path: str) -> list:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM content_ideas WHERE status = 'approved' ORDER BY created_at"
        ).fetchall()
        return [ContentIdea.from_row(row) for row in rows]


def get_next_idea_for_video(db_path: str) -> Optional[ContentIdea]:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM content_ideas
            WHERE status = 'approved' AND video_status IS NULL
            ORDER BY created_at
            LIMIT 1
            """
        ).fetchone()
        return ContentIdea.from_row(row) if row else None


def mark_video_processing(db_path: str, idea_id: int) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE content_ideas SET video_status = 'processing', video_error = NULL WHERE id = ?",
            (idea_id,),
        )


def mark_video_ready(db_path: str, idea_id: int, video_path: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE content_ideas SET video_status = 'ready', video_path = ? WHERE id = ?",
            (video_path, idea_id),
        )


def mark_video_failed(db_path: str, idea_id: int, error: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE content_ideas SET video_status = 'failed', video_error = ? WHERE id = ?",
            (error, idea_id),
        )


def set_video_telegram_message_id(db_path: str, idea_id: int, telegram_message_id: int) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE content_ideas SET video_telegram_message_id = ? WHERE id = ?",
            (telegram_message_id, idea_id),
        )


def update_video_status(db_path: str, idea_id: int, status: str) -> None:
    if status not in VIDEO_STATUSES:
        raise ValueError(f"Invalid video status: {status}")
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE content_ideas SET video_status = ? WHERE id = ?",
            (status, idea_id),
        )


def reset_video_status(db_path: str, idea_id: int) -> None:
    """Clears video state so the worker picks the idea up again on its next tick."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            UPDATE content_ideas
            SET video_status = NULL, video_path = NULL, video_error = NULL
            WHERE id = ?
            """,
            (idea_id,),
        )


def get_by_video_telegram_message_id(db_path: str, telegram_message_id: int) -> Optional[ContentIdea]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM content_ideas WHERE video_telegram_message_id = ?", (telegram_message_id,)
        ).fetchone()
        return ContentIdea.from_row(row) if row else None
