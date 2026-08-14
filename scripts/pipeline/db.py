"""Shared SQLite helpers for the corpus enrichment pipeline."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "corpus.db"


def get_conn(db_path=DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_columns(conn: sqlite3.Connection, table: str = "questions") -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def ensure_pipeline_progress_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pipeline_progress (
            phase TEXT NOT NULL,
            question_id TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            started_at TEXT,
            completed_at TEXT,
            PRIMARY KEY (phase, question_id)
        )
        """
    )
    conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_progress_status(conn: sqlite3.Connection, phase: str, question_id: str) -> str | None:
    row = conn.execute(
        "SELECT status FROM pipeline_progress WHERE phase=? AND question_id=?",
        (phase, question_id),
    ).fetchone()
    return row["status"] if row else None


def mark_progress(
    conn: sqlite3.Connection,
    phase: str,
    question_id: str,
    status: str,
    result: str | None = None,
    started_at: str | None = None,
) -> None:
    completed_at = now_iso() if status in ("done", "error") else None
    conn.execute(
        """
        INSERT INTO pipeline_progress (phase, question_id, status, result, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(phase, question_id) DO UPDATE SET
            status=excluded.status,
            result=excluded.result,
            completed_at=excluded.completed_at
        """,
        (phase, question_id, status, result, started_at or now_iso(), completed_at),
    )
    conn.commit()


def is_phase_complete(conn: sqlite3.Connection, phase: str, total: int | None = None) -> bool:
    if total is None:
        total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    done = conn.execute(
        "SELECT COUNT(*) FROM pipeline_progress WHERE phase=? AND status='done'", (phase,)
    ).fetchone()[0]
    return done >= total


def done_ids(conn: sqlite3.Connection, phase: str) -> set[str]:
    rows = conn.execute(
        "SELECT question_id FROM pipeline_progress WHERE phase=? AND status='done'", (phase,)
    ).fetchall()
    return {r["question_id"] for r in rows}
