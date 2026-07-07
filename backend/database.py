import sqlite3
from pathlib import Path
from typing import Iterable


DB_PATH = Path(__file__).resolve().parent / "chatbot.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                rating INTEGER
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS insights (
                session_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                user_need TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                satisfaction INTEGER NOT NULL,
                urgency TEXT NOT NULL,
                summary TEXT NOT NULL,
                hidden_topic TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def ensure_session(session_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
            (session_id,),
        )


def save_message(session_id: str, role: str, content: str) -> None:
    ensure_session(session_id)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content),
        )


def get_messages(session_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def end_session(session_id: str, rating: int) -> None:
    ensure_session(session_id)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET ended_at = CURRENT_TIMESTAMP,
                rating = ?
            WHERE session_id = ?
            """,
            (rating, session_id),
        )


def save_insight(insight: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO insights (
                session_id,
                category,
                user_need,
                sentiment,
                satisfaction,
                urgency,
                summary,
                hidden_topic,
                recommended_action
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                category = excluded.category,
                user_need = excluded.user_need,
                sentiment = excluded.sentiment,
                satisfaction = excluded.satisfaction,
                urgency = excluded.urgency,
                summary = excluded.summary,
                hidden_topic = excluded.hidden_topic,
                recommended_action = excluded.recommended_action,
                created_at = CURRENT_TIMESTAMP
            """,
            (
                insight["session_id"],
                insight["category"],
                insight["user_need"],
                insight["sentiment"],
                insight["satisfaction"],
                insight["urgency"],
                insight["summary"],
                insight["hidden_topic"],
                insight["recommended_action"],
            ),
        )


def list_insights(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                session_id,
                category,
                user_need,
                sentiment,
                satisfaction,
                urgency,
                summary,
                hidden_topic,
                recommended_action,
                created_at
            FROM insights
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def seed_demo_messages(session_id: str, messages: Iterable[tuple[str, str]]) -> None:
    ensure_session(session_id)
    for role, content in messages:
        save_message(session_id, role, content)
