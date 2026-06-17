import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot Credentials ──────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in .env")

# ── Admin Settings ───────────────────────────────────────────────────────────
# Comma-separated list of admin Telegram user IDs in .env
# e.g. ADMIN_IDS=123456789,987654321
ADMIN_IDS: list[int] = [
    int(i.strip())
    for i in os.getenv("ADMIN_IDS", "").split(",")
    if i.strip().isdigit()
]

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "datemex.db")

# ── Anti-Spam / Flood Settings ───────────────────────────────────────────────
FLOOD_MAX_MESSAGES: int = 8          # messages allowed in the window
FLOOD_WINDOW_SECONDS: int = 10       # sliding window in seconds
FLOOD_MUTE_SECONDS: int = 60         # how long to mute after flood

DUPLICATE_WINDOW_SECONDS: int = 30   # window to detect duplicate messages
DUPLICATE_MAX_COUNT: int = 3         # how many identical messages trigger action

# ── Media Unlock ─────────────────────────────────────────────────────────────
MEDIA_UNLOCK_SECONDS: int = 120      # seconds before media is unlocked in a session

# ── Conversation States ───────────────────────────────────────────────────────
AGE, GENDER, COUNTRY, STATE_IN = range(4)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
