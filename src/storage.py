import json
import sqlite3
from pathlib import Path

from src.models import Classification, JobPosting

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    dedupe_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    relevant INTEGER NOT NULL,
    is_likely_fake INTEGER NOT NULL,
    apply_probability INTEGER NOT NULL,
    first_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kv_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def is_seen(conn: sqlite3.Connection, job: JobPosting) -> bool:
    row = conn.execute(
        "SELECT 1 FROM seen_jobs WHERE dedupe_key = ?", (job.dedupe_key,)
    ).fetchone()
    return row is not None


def save_classification(conn: sqlite3.Connection, c: Classification) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO seen_jobs
            (dedupe_key, title, company, url, source, relevant, is_likely_fake, apply_probability, first_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            c.job.dedupe_key,
            c.job.title,
            c.job.company,
            c.job.url,
            c.job.source,
            int(c.relevant),
            int(c.is_likely_fake),
            c.apply_probability,
        ),
    )
    conn.commit()


def get_state(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM kv_state WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO kv_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
