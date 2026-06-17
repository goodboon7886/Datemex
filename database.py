"""
database.py – All SQLite interactions for DatemexBot.
Tables: users, groups, warnings, reports, settings, keywords, spam_logs
"""

import sqlite3
import time
import logging
from contextlib import contextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)


# ── Connection helper ─────────────────────────────────────────────────────────

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema bootstrap ──────────────────────────────────────────────────────────

def init_db():
    """Create all tables if they do not exist."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id         INTEGER PRIMARY KEY,
            username        TEXT,
            first_name      TEXT,
            age             TEXT,
            gender          TEXT,
            state           TEXT,
            partner_id      INTEGER,
            last_session    TEXT,
            session_start   REAL,
            is_banned       INTEGER DEFAULT 0,
            ban_reason      TEXT,
            warn_count      INTEGER DEFAULT 0,
            is_muted        INTEGER DEFAULT 0,
            mute_until      REAL    DEFAULT 0,
            joined_at       REAL    DEFAULT (strftime('%s','now')),
            last_seen       REAL    DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS groups (
            group_id        INTEGER PRIMARY KEY,
            title           TEXT,
            added_at        REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS warnings (
            warn_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            admin_id        INTEGER NOT NULL,
            reason          TEXT,
            issued_at       REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id     INTEGER NOT NULL,
            session_id      TEXT    NOT NULL,
            reason          TEXT,
            reviewed        INTEGER DEFAULT 0,
            reported_at     REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key             TEXT PRIMARY KEY,
            value           TEXT
        );

        CREATE TABLE IF NOT EXISTS keywords (
            keyword         TEXT PRIMARY KEY,
            added_by        INTEGER,
            added_at        REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS spam_logs (
            log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            event_type      TEXT    NOT NULL,
            detail          TEXT,
            logged_at       REAL DEFAULT (strftime('%s','now'))
        );
        """)
    logger.info("Database initialised at %s", DB_PATH)


# ── User helpers ──────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str | None, first_name: str | None):
    """Insert or update basic telegram identity. Called on every interaction."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_seen  = excluded.last_seen
        """, (user_id, username, first_name, time.time()))


def set_profile(user_id: int, age: str, gender: str, state: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET age=?, gender=?, state=? WHERE user_id=?
        """, (age, gender, state, user_id))


def get_user(user_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def set_partner(user_id: int, partner_id: int | None, session_id: str | None):
    start = time.time() if partner_id else None
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET partner_id=?, last_session=?, session_start=?
            WHERE user_id=?
        """, (partner_id, session_id, start, user_id))


def is_registered(user_id: int) -> bool:
    row = get_user(user_id)
    return row is not None and row["age"] is not None


def is_banned(user_id: int) -> bool:
    row = get_user(user_id)
    return bool(row and row["is_banned"])


def ban_user(user_id: int, reason: str = ""):
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?
        """, (reason, user_id))


def unban_user(user_id: int):
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=?
        """, (user_id,))


def get_all_users() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE is_banned=0").fetchall()


def get_stats() -> dict:
    with get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        banned  = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
        active  = conn.execute("SELECT COUNT(*) FROM users WHERE partner_id IS NOT NULL").fetchone()[0]
        reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        warns   = conn.execute("SELECT COUNT(*) FROM warnings").fetchone()[0]
    return {"total": total, "banned": banned, "active": active,
            "reports": reports, "warnings": warns}


# ── Mute helpers ──────────────────────────────────────────────────────────────

def mute_user(user_id: int, duration_sec: int):
    until = time.time() + duration_sec
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET is_muted=1, mute_until=? WHERE user_id=?
        """, (until, user_id))


def is_muted(user_id: int) -> bool:
    row = get_user(user_id)
    if not row or not row["is_muted"]:
        return False
    if time.time() > row["mute_until"]:
        unmute_user(user_id)
        return False
    return True


def unmute_user(user_id: int):
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET is_muted=0, mute_until=0 WHERE user_id=?
        """, (user_id,))


# ── Warning helpers ───────────────────────────────────────────────────────────

def add_warning(user_id: int, admin_id: int, reason: str = "") -> int:
    """Returns new total warning count for the user."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO warnings (user_id, admin_id, reason) VALUES (?,?,?)
        """, (user_id, admin_id, reason))
        conn.execute("""
            UPDATE users SET warn_count = warn_count + 1 WHERE user_id=?
        """, (user_id,))
        row = conn.execute("SELECT warn_count FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row["warn_count"] if row else 1


def get_warnings(user_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM warnings WHERE user_id=? ORDER BY issued_at DESC
        """, (user_id,)).fetchall()


# ── Report helpers ────────────────────────────────────────────────────────────

def add_report(reporter_id: int, session_id: str, reason: str = ""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reports (reporter_id, session_id, reason) VALUES (?,?,?)
        """, (reporter_id, session_id, reason))


def get_pending_reports() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM reports WHERE reviewed=0 ORDER BY reported_at DESC
        """).fetchall()


def mark_report_reviewed(report_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE reports SET reviewed=1 WHERE report_id=?", (report_id,))


# ── Keyword helpers ───────────────────────────────────────────────────────────

def add_keyword(keyword: str, admin_id: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO keywords (keyword, added_by) VALUES (?,?)
        """, (keyword.lower(), admin_id))


def remove_keyword(keyword: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM keywords WHERE keyword=?", (keyword.lower(),))


def get_keywords() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT keyword FROM keywords").fetchall()
    return [r["keyword"] for r in rows]


# ── Spam log helpers ──────────────────────────────────────────────────────────

def log_spam(user_id: int, event_type: str, detail: str = ""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO spam_logs (user_id, event_type, detail) VALUES (?,?,?)
        """, (user_id, event_type, detail))


# ── Group helpers ─────────────────────────────────────────────────────────────

def upsert_group(group_id: int, title: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO groups (group_id, title) VALUES (?,?)
            ON CONFLICT(group_id) DO UPDATE SET title=excluded.title
        """, (group_id, title))


# ── Settings helpers ──────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO settings (key, value) VALUES (?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value))
