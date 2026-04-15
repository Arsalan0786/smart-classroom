"""
db/database.py  —  SQLite persistence for Smart Classroom
Tables
──────
sessions  : one row per start/stop detection run
frames    : one row per processed frame (linked to sessions)
"""

import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "classroom.db"

_local = threading.local()   # thread-local connections


def _conn():
    """Return a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent writes
    return _local.conn


def init_db():
    """Create tables if they do not exist."""
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type  TEXT    NOT NULL,
                started_at   REAL    NOT NULL,   -- Unix timestamp
                ended_at     REAL,
                total_frames INTEGER DEFAULT 0,
                peak_persons INTEGER DEFAULT 0,
                avg_persons  REAL    DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS frames (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                frame_no   INTEGER NOT NULL,
                ts         REAL    NOT NULL,    -- Unix timestamp
                fps        REAL    DEFAULT 0,
                q1         INTEGER DEFAULT 0,
                q2         INTEGER DEFAULT 0,
                q3         INTEGER DEFAULT 0,
                q4         INTEGER DEFAULT 0,
                total      INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_frames_session
                ON frames(session_id);
        """)
    print(f"[DB] Ready → {DB_PATH}")


# ── Session lifecycle ─────────────────────────────────────────────────────────
def start_session(source_type: str) -> int:
    """Insert a new session row and return its id."""
    c = _conn()
    cur = c.execute(
        "INSERT INTO sessions (source_type, started_at) VALUES (?, ?)",
        (source_type, time.time()),
    )
    c.commit()
    return cur.lastrowid


def end_session(session_id: int):
    """Close the session: write end time and aggregate stats."""
    c = _conn()
    c.execute("""
        UPDATE sessions
        SET ended_at     = ?,
            total_frames = (SELECT COUNT(*)  FROM frames WHERE session_id = ?),
            peak_persons = (SELECT MAX(total) FROM frames WHERE session_id = ?),
            avg_persons  = (SELECT AVG(total) FROM frames WHERE session_id = ?)
        WHERE id = ?
    """, (time.time(), session_id, session_id, session_id, session_id))
    c.commit()


# ── Frame recording ───────────────────────────────────────────────────────────
_BATCH: list   = []
_BATCH_LOCK    = threading.Lock()
_BATCH_SIZE    = 30          # flush to DB every N frames


def record_frame(session_id: int, frame_no: int, fps: float,
                 q1: int, q2: int, q3: int, q4: int):
    """Buffer a frame record; flush to DB in batches."""
    total = q1 + q2 + q3 + q4
    row   = (session_id, frame_no, time.time(), fps, q1, q2, q3, q4, total)
    with _BATCH_LOCK:
        _BATCH.append(row)
        if len(_BATCH) >= _BATCH_SIZE:
            _flush()


def flush_all():
    """Force-flush any remaining buffered rows."""
    with _BATCH_LOCK:
        _flush()


def _flush():
    """Must be called with _BATCH_LOCK held."""
    if not _BATCH:
        return
    c = _conn()
    c.executemany(
        """INSERT INTO frames
           (session_id, frame_no, ts, fps, q1, q2, q3, q4, total)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        _BATCH,
    )
    c.commit()
    _BATCH.clear()


# ── Query helpers ─────────────────────────────────────────────────────────────
def get_sessions(limit: int = 50) -> list[dict]:
    rows = _conn().execute(
        """SELECT id, source_type, started_at, ended_at,
                  total_frames, peak_persons, ROUND(avg_persons,2) as avg_persons
           FROM sessions
           ORDER BY id DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_session_frames(session_id: int, downsample: int = 1) -> list[dict]:
    """Return frame rows for a session, optionally downsampled."""
    rows = _conn().execute(
        """SELECT frame_no, ts, fps, q1, q2, q3, q4, total
           FROM frames
           WHERE session_id = ? AND frame_no % ? = 0
           ORDER BY frame_no""",
        (session_id, max(1, downsample)),
    ).fetchall()
    return [dict(r) for r in rows]


def get_analytics() -> dict:
    """Global aggregate stats across all sessions."""
    c   = _conn()
    row = c.execute("""
        SELECT
            COUNT(DISTINCT s.id)          AS total_sessions,
            COALESCE(SUM(s.total_frames),0) AS total_frames,
            COALESCE(MAX(s.peak_persons),0) AS all_time_peak,
            COALESCE(AVG(s.avg_persons) ,0) AS overall_avg
        FROM sessions s
        WHERE s.total_frames > 0
    """).fetchone()
    return dict(row) if row else {}


def get_hourly_summary() -> list[dict]:
    """Persons detected per hour, last 24 h (for the history bar chart)."""
    rows = _conn().execute("""
        SELECT
            CAST(ts / 3600 AS INT) * 3600        AS hour_ts,
            ROUND(AVG(total), 2)                  AS avg_persons,
            MAX(total)                            AS peak_persons,
            COUNT(*)                              AS frame_count
        FROM frames
        WHERE ts >= strftime('%s','now','-1 day')
        GROUP BY hour_ts
        ORDER BY hour_ts
    """).fetchall()
    return [dict(r) for r in rows]


def get_session_timeline(session_id: int) -> list[dict]:
    """Lightweight per-frame timeline for the selected session chart."""
    rows = _conn().execute(
        """SELECT frame_no, q1, q2, q3, q4, total
           FROM frames
           WHERE session_id = ?
           ORDER BY frame_no""",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]
