"""
app.py – DatemexBot  |  Anonymous Chat Bot
Main entry point: wires all handlers together.
"""

import logging
import time
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)

import database as db
import utils
import admin as adm
from config import (
    BOT_TOKEN, LOG_LEVEL,
    AGE, GENDER, COUNTRY, STATE_IN,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  REGISTRATION  CONVERSATION
# ─────────────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)

    if db.is_banned(user.id):
        await update.message.reply_text("⛔ You have been banned from this bot.")
        return ConversationHandler.END

    # Already registered? Skip straight to chat prompt
    if db.is_registered(user.id):
        keyboard = [[InlineKeyboardButton("💬 Start Chatting", callback_data="go_chat")]]
        await update.message.reply_text(
            f"👋 Welcome back, <b>{user.first_name}</b>!\n\n"
            "Your profile is already set up. Ready to meet someone?",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🌟 <b>Welcome to DatemexBot!</b>\n\n"
        "Let's set up your profile in a few quick steps.\n\n"
        "How old are you? (e.g. 23)",
        parse_mode=ParseMode.HTML
    )
    return AGE


async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age_text = update.message.text.strip()
    if not age_text.isdigit() or not (13 <= int(age_text) <= 99):
        await update.message.reply_text("❌ Please enter a valid age (13–99):")
        return AGE

    context.user_data["age"] = age_text
    keyboard = [
        [InlineKeyboardButton("👱‍♂️ Male", callback_data="Male"),
         InlineKeyboardButton("👩 Female", callback_data="Female"),
         InlineKeyboardButton("⚧ Other", callback_data="Other")]
    ]
    await update.message.reply_text("Select your gender:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GENDER


async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["gender"] = query.data

    country_rows = [
        ["🇮🇳 India", "🇺🇸 America", "🇬🇧 UK", "🇨🇦 Canada"],
        ["🇦🇺 Australia", "🇩🇪 Germany", "🇫🇷 France", "🇯🇵 Japan"],
        ["🇧🇷 Brazil", "🇷🇺 Russia", "🇨🇳 China", "🇰🇷 South Korea"],
        ["🇮🇩 Indonesia", "🇸🇦 Saudi Arabia", "🇮🇷 Iran", "🇳🇬 Nigeria"],
        ["🇪🇸 Spain", "🇮🇹 Italy", "🇲🇾 Malaysia", "🇵🇰 Pakistan"],
        ["🇿🇦 South Africa", "🇪🇹 Ethiopia", "🇦🇷 Argentina", "🇪🇬 Egypt"],
    ]

    buttons = [
        [InlineKeyboardButton(label, callback_data=label.split(" ", 1)[1])
         for label in row]
        for row in country_rows
    ]
    await query.edit_message_text("🌍 Select your country:", reply_markup=InlineKeyboardMarkup(buttons))
    return COUNTRY


async def get_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country = query.data
    context.user_data["country"] = country

    if country == "India":
        indian_states = [
            "Andaman & Nicobar", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
            "Bihar", "Chandigarh", "Chhattisgarh", "Dadra & Nagar Haveli",
            "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
            "Jammu & Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh",
            "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
            "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan",
            "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
            "Uttarakhand", "West Bengal"
        ]
        btns = [
            [InlineKeyboardButton(indian_states[i], callback_data=indian_states[i])] +
            ([InlineKeyboardButton(indian_states[i+1], callback_data=indian_states[i+1])]
             if i+1 < len(indian_states) else [])
            for i in range(0, len(indian_states), 2)
        ]
        await query.edit_message_text("🇮🇳 Select your state:", reply_markup=InlineKeyboardMarkup(btns))
        return STATE_IN
    else:
        _finish_registration(query.from_user.id, context, country)
        await _send_registration_success(query)
        return ConversationHandler.END


async def get_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = query.data
    _finish_registration(query.from_user.id, context, f"India - {state}")
    await _send_registration_success(query)
    return ConversationHandler.END


def _finish_registration(user_id: int, context: ContextTypes.DEFAULT_TYPE, location: str):
    db.set_profile(
        user_id,
        age=context.user_data["age"],
        gender=context.user_data["gender"],
        state=location
    )


async def _send_registration_success(query):
    """BUG FIX: After registration success show /chat button instead of plain text."""
    keyboard = [[InlineKeyboardButton("💬 Start Chatting Now!", callback_data="go_chat")]]
    await query.edit_message_text(
        "✅ <b>Profile registered successfully!</b>\n\n"
        "You're all set. Tap below to find a chat partner 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled. Type /start to try again.")
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await _start_matching(user_id, update, context)


async def _start_matching(user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Core matching logic, reused by /chat and the inline button."""
    if db.is_banned(user_id):
        await _reply(update, context, user_id, "⛔ You have been banned from this bot.")
        return

    if not db.is_registered(user_id):
        await _reply(update, context, user_id, "⚠️ Please register first by typing /start")
        return

    row = db.get_user(user_id)
    if row and row["partner_id"]:
        await _reply(update, context, user_id, "ℹ️ You are already connected to a partner!")
        return

    if user_id in utils.queue:
        await _reply(update, context, user_id, "🔎 Still searching… please wait.")
        return

    # Try to pair with someone in the queue
    if utils.queue:
        partner_id = utils.queue.pop(0)
        session_id = utils.generate_session_tag()

        db.set_partner(user_id, partner_id, session_id)
        db.set_partner(partner_id, user_id, session_id)

        partner_row = db.get_user(partner_id)
        user_row    = db.get_user(user_id)

        await context.bot.send_message(user_id,    utils.build_match_card(partner_row), parse_mode=ParseMode.HTML)
        await context.bot.send_message(partner_id, utils.build_match_card(user_row),    parse_mode=ParseMode.HTML)
    else:
        utils.queue.append(user_id)
        await _reply(update, context, user_id,
                     "🔎 Looking for a partner… please wait.\n\nType /exit to cancel the search.")


async def cmd_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = db.get_user(user_id)
    if not row:
        return

    partner_id = row["partner_id"]
    session_id = row["last_session"]

    if partner_id:
        db.set_partner(user_id, None, None)
        db.set_partner(partner_id, None, None)
        card = utils.build_disconnect_card(session_id or "N/A")
        keyboard = [[InlineKeyboardButton("⚠️ Report", callback_data=f"report_{session_id}")]]
        rm = InlineKeyboardMarkup(keyboard)
        try:
            await update.message.reply_text(card, parse_mode=ParseMode.HTML, reply_markup=rm)
        except Exception:
            pass
        try:
            await context.bot.send_message(partner_id, card, parse_mode=ParseMode.HTML, reply_markup=rm)
        except Exception:
            pass
    elif user_id in utils.queue:
        utils.queue.remove(user_id)
        await update.message.reply_text("🔍 Search cancelled.")
    else:
        await update.message.reply_text("ℹ️ You are not in a chat right now.")


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = db.get_user(user_id)
    if not row:
        return

    partner_id = row["partner_id"]
    session_id = row["last_session"]

    if partner_id:
        db.set_partner(user_id, None, None)
        db.set_partner(partner_id, None, None)
        card = utils.build_disconnect_card(session_id or "N/A")
        keyboard = [[InlineKeyboardButton("⚠️ Report", callback_data=f"report_{session_id}")]]
        try:
            await context.bot.send_message(
                partner_id, card, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            pass

    if user_id in utils.queue:
        utils.queue.remove(user_id)

    await _start_matching(user_id, update, context)


# ─────────────────────────────────────────────────────────────────────────────
#  RECHAT  – reconnect to a previous session partner
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_rechat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_registered(user_id):
        await update.message.reply_text("⚠️ Please register first by typing /start")
        return

    if not context.args:
        await update.message.reply_text("Usage: /rechat <session_tag>")
        return

    session_id = context.args[0].upper()
    row = db.get_user(user_id)
    if not row or row["last_session"] != session_id:
        await update.message.reply_text("❌ Session tag not found or doesn't belong to you.")
        return

    if row["partner_id"]:
        await update.message.reply_text("ℹ️ You are already in a chat. Use /exit first.")
        return

    # Can't auto-reconnect unless both agree – put user in queue and notify
    await update.message.reply_text(
        "🔁 Rechat request sent for session <code>{}</code>.\n"
        "If your previous partner also uses /rechat with the same tag you'll be reconnected.\n\n"
        "In the meantime you're added to the general queue.".format(session_id),
        parse_mode=ParseMode.HTML
    )
    await _start_matching(user_id, update, context)


# ─────────────────────────────────────────────────────────────────────────────
#  REPORT
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        row = db.get_user(user_id)
        session_id = row["last_session"] if row else None
        if not session_id:
            await update.message.reply_text("Usage: /report <session_tag> [reason]")
            return
    else:
        session_id = context.args[0].upper()

    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else ""
    db.add_report(user_id, session_id, reason)
    await update.message.reply_text(
        f"✅ Report submitted for session <code>{session_id}</code>.\n"
        "Our team will review this.",
        parse_mode=ParseMode.HTML
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /stats
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Public stats (light version)
    stats = db.get_stats()
    await update.message.reply_text(
        "📊 <b>Bot Stats</b>\n\n"
        f"👤 Total users  : <b>{stats['total']}</b>\n"
        f"💬 Active chats : <b>{stats['active'] // 2}</b>\n"
        f"🔎 In queue     : <b>{len(utils.queue)}</b>",
        parse_mode=ParseMode.HTML
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /help
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 <b>DatemexBot Help</b>\n\n"
        "<b>Getting started</b>\n"
        "  /start  — Register / view profile\n"
        "  /chat   — Find a chat partner\n\n"
        "<b>During a chat</b>\n"
        "  /next   — Skip to next partner\n"
        "  /exit   — Leave the current chat\n\n"
        "<b>Other</b>\n"
        "  /rechat &lt;tag&gt;  — Reconnect to a past session\n"
        "  /report &lt;tag&gt;  — Report a user\n"
        "  /stats             — View bot statistics\n"
        "  /help              — Show this help\n\n"
        "🚫 Sharing links, usernames, or restricted content is blocked.",
        parse_mode=ParseMode.HTML
    )


# ─────────────────────────────────────────────────────────────────────────────
#  INLINE BUTTON CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "go_chat":
        # Inline "Start chatting" button after registration
        await query.edit_message_reply_markup(reply_markup=None)
        await _start_matching(user_id, update, context)

    elif data.startswith("report_"):
        session_id = data.split("_", 1)[1]
        db.add_report(user_id, session_id)
        await query.edit_message_text(
            f"✅ Report submitted for session <code>{session_id}</code>. Thank you!",
            parse_mode=ParseMode.HTML
        )


# ─────────────────────────────────────────────────────────────────────────────
#  MESSAGE FORWARDING  (anonymous relay)
# ─────────────────────────────────────────────────────────────────────────────

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.upsert_user(user_id, update.effective_user.username, update.effective_user.first_name)

    if db.is_banned(user_id):
        return

    # ── Flood check ──
    if utils.check_flood(user_id):
        await update.message.reply_text(
            f"⚠️ You are sending messages too fast. Please wait a moment."
        )
        return

    # ── Mute check ──
    if db.is_muted(user_id):
        await update.message.reply_text("🔇 You are temporarily muted due to spam.")
        return

    row = db.get_user(user_id)
    if not row or not row["partner_id"]:
        await update.message.reply_text(
            "💬 You are not in a chat.\n"
            "Type /chat to find a partner or /help for all commands."
        )
        return

    partner_id    = row["partner_id"]
    session_start = row["session_start"]

    # ── Text message ──────────────────────────────────────────────────────
    if update.message.text:
        text = update.message.text

        # Duplicate detection
        if utils.check_duplicate(user_id, text):
            await update.message.reply_text("⚠️ Please don't send the same message repeatedly.")
            return

        # Link / keyword filter
        allowed, reason = utils.is_message_allowed(text)
        if not allowed:
            await update.message.reply_text(reason)
            return

        try:
            await context.bot.send_message(partner_id, text)
        except Exception as e:
            logger.error("Failed to forward text to %s: %s", partner_id, e)

    # ── Photo ─────────────────────────────────────────────────────────────
    elif update.message.photo:
        if not utils.media_unlocked(session_start):
            await update.message.reply_text("⏱ Media sharing unlocks after 2 minutes in a chat.")
            return
        caption = update.message.caption or ""
        try:
            await context.bot.send_photo(partner_id, update.message.photo[-1].file_id, caption=caption)
        except Exception as e:
            logger.error("Failed to forward photo to %s: %s", partner_id, e)

    # ── Sticker ───────────────────────────────────────────────────────────
    elif update.message.sticker:
        try:
            await context.bot.send_sticker(partner_id, update.message.sticker.file_id)
        except Exception as e:
            logger.error("Failed to forward sticker to %s: %s", partner_id, e)

    # ── Video ─────────────────────────────────────────────────────────────
    elif update.message.video:
        if not utils.media_unlocked(session_start):
            await update.message.reply_text("⏱ Media sharing unlocks after 2 minutes in a chat.")
            return
        caption = update.message.caption or ""
        try:
            await context.bot.send_video(partner_id, update.message.video.file_id, caption=caption)
        except Exception as e:
            logger.error("Failed to forward video to %s: %s", partner_id, e)

    # ── Voice ─────────────────────────────────────────────────────────────
    elif update.message.voice:
        if not utils.media_unlocked(session_start):
            await update.message.reply_text("⏱ Media sharing unlocks after 2 minutes in a chat.")
            return
        try:
            await context.bot.send_voice(partner_id, update.message.voice.file_id)
        except Exception as e:
            logger.error("Failed to forward voice to %s: %s", partner_id, e)


# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL ERROR HANDLER
# ─────────────────────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception", exc_info=context.error)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER  – unified reply for update or context.bot
# ─────────────────────────────────────────────────────────────────────────────

async def _reply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    try:
        if update.message:
            await update.message.reply_text(text)
        else:
            await context.bot.send_message(user_id, text)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  BOT COMMANDS  (shows up in Telegram menu)
# ─────────────────────────────────────────────────────────────────────────────

async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start",          "Register / view profile"),
        BotCommand("chat",           "Find a chat partner"),
        BotCommand("next",           "Skip to next partner"),
        BotCommand("exit",           "Leave current chat"),
        BotCommand("rechat",         "Reconnect to past session"),
        BotCommand("report",         "Report a user"),
        BotCommand("stats",          "View bot statistics"),
        BotCommand("help",           "Show all commands"),
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ── Registration conversation ──────────────────────────────────────────
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER:   [CallbackQueryHandler(get_gender)],
            COUNTRY:  [CallbackQueryHandler(get_country)],
            STATE_IN: [CallbackQueryHandler(get_state)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
        # Removed per_message=False to eliminate the PTBUserWarning
    )
    app.add_handler(conv)

    # ── Chat commands ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("chat",    cmd_chat))
    app.add_handler(CommandHandler("exit",    cmd_exit))
    app.add_handler(CommandHandler("next",    cmd_next))
    app.add_handler(CommandHandler("rechat",  cmd_rechat))
    app.add_handler(CommandHandler("report",  cmd_report))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("help",    cmd_help))

    # ── Admin commands ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("admin",          adm.admin_dashboard))
    app.add_handler(CommandHandler("ban",            adm.ban_user_cmd))
    app.add_handler(CommandHandler("unban",          adm.unban_user_cmd))
    app.add_handler(CommandHandler("warn",           adm.warn
