"""
utils.py – Utility helpers: session tags, anti-spam, flood detection,
           duplicate detection, link/keyword filtering.
"""

import random
import string
import time
import hashlib
import logging
from collections import defaultdict, deque
from config import (
    FLOOD_MAX_MESSAGES, FLOOD_WINDOW_SECONDS, FLOOD_MUTE_SECONDS,
    DUPLICATE_WINDOW_SECONDS, DUPLICATE_MAX_COUNT, MEDIA_UNLOCK_SECONDS,
)
import database as db

logger = logging.getLogger(__name__)

# ── In-memory anti-spam state ─────────────────────────────────────────────────
# { user_id: deque of timestamps }
_flood_tracker: dict[int, deque] = defaultdict(deque)

# { user_id: { msg_hash: deque of timestamps } }
_dup_tracker: dict[int, dict[str, deque]] = defaultdict(lambda: defaultdict(deque))

# ── Queue (in-memory, fast) ───────────────────────────────────────────────────
queue: list[int] = []


# ── Session tag ───────────────────────────────────────────────────────────────

def generate_session_tag() -> str:
    """Returns a random 8-character alphanumeric session tag."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ── Flood detection ───────────────────────────────────────────────────────────

def check_flood(user_id: int) -> bool:
    """
    Returns True (and auto-mutes the user) if the user is flooding.
    Call this before processing every message.
    """
    now = time.time()
    window = _flood_tracker[user_id]

    # Drop timestamps outside the window
    while window and now - window[0] > FLOOD_WINDOW_SECONDS:
        window.popleft()

    window.append(now)

    if len(window) > FLOOD_MAX_MESSAGES:
        db.mute_user(user_id, FLOOD_MUTE_SECONDS)
        db.log_spam(user_id, "flood", f"{len(window)} msgs in {FLOOD_WINDOW_SECONDS}s")
        logger.warning("Flood detected for user %s", user_id)
        return True
    return False


# ── Duplicate message detection ───────────────────────────────────────────────

def check_duplicate(user_id: int, text: str) -> bool:
    """
    Returns True if the user sent the same message too many times recently.
    """
    now = time.time()
    h = hashlib.md5(text.encode()).hexdigest()
    window = _dup_tracker[user_id][h]

    while window and now - window[0] > DUPLICATE_WINDOW_SECONDS:
        window.popleft()

    window.append(now)

    if len(window) >= DUPLICATE_MAX_COUNT:
        db.log_spam(user_id, "duplicate", text[:80])
        logger.warning("Duplicate spam from user %s", user_id)
        return True
    return False


# ── Link / keyword filter ─────────────────────────────────────────────────────

_LINK_PATTERNS = ("http://", "https://", "t.me/", "telegram.me/", "@")


def contains_link(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in _LINK_PATTERNS)


def contains_banned_keyword(text: str) -> bool:
    keywords = db.get_keywords()
    low = text.lower()
    return any(kw in low for kw in keywords)


def is_message_allowed(text: str) -> tuple[bool, str]:
    """
    Returns (allowed, reason).  reason is '' when allowed.
    """
    if contains_link(text):
        return False, "🚫 Links and usernames are restricted to prevent scams!"
    if contains_banned_keyword(text):
        return False, "🚫 Your message contains a restricted word."
    return True, ""


# ── Media unlock check ────────────────────────────────────────────────────────

def media_unlocked(session_start: float | None) -> bool:
    """Returns True if enough time has passed since the session started."""
    if session_start is None:
        return False
    return (time.time() - session_start) >= MEDIA_UNLOCK_SECONDS


# ── Match card builder ────────────────────────────────────────────────────────

def build_match_card(target: dict | object) -> str:
    """
    Accepts either a sqlite3.Row or a plain dict with keys:
    age, gender, state.
    """
    age    = target["age"]
    gender = target["gender"]
    state  = target["state"]

    return (
        "✅ <b>Partner Matched!</b>\n\n"
        f"🔢 <b>Age:</b> {age}\n"
        f"👥 <b>Gender:</b> <tg-spoiler>{gender}</tg-spoiler>\n"
        f"🌍 <b>Location:</b> {state}\n\n"
        "🚫 <i>Links are restricted</i>\n"
        "⏱ <i>Media unlocks after 2 minutes</i>\n\n"
        "/next — Skip to next partner\n"
        "/exit — Leave the chat"
    )


def build_disconnect_card(session_id: str) -> str:
    return (
        "🚫 <b>Partner left the chat</b>\n\n"
        "/chat — Find a new partner\n"
        "───────────────\n"
        f"⚠️ <b>Session TAG:</b> <code>{session_id}</code>\n\n"
        f"<i>Reconnect:</i> /rechat {session_id}\n"
        f"<i>Report:</i> /report {session_id}"
    )
