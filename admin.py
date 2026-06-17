"""
admin.py – Admin-only commands:
    /admin  /ban  /unban  /warn  /broadcast  /setkeyword  /removekeyword
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import database as db
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


# ── Guard decorator ───────────────────────────────────────────────────────────

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ You are not authorised to use this command.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


# ── /admin  – dashboard ───────────────────────────────────────────────────────

@admin_only
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_stats()
    reports = db.get_pending_reports()
    keywords = db.get_keywords()

    pending_txt = "\n".join(
        f"  #{r['report_id']} — Session <code>{r['session_id']}</code> — {r['reported_at']:.0f}"
        for r in reports[:5]
    ) or "  None"

    kw_txt = ", ".join(f"<code>{k}</code>" for k in keywords) or "None"

    msg = (
        "🛡 <b>Admin Dashboard</b>\n\n"
        f"👤 Total users : <b>{stats['total']}</b>\n"
        f"🔴 Banned      : <b>{stats['banned']}</b>\n"
        f"💬 In chat     : <b>{stats['active']}</b>\n"
        f"⚠️ Reports     : <b>{stats['reports']}</b>\n"
        f"🚩 Warnings    : <b>{stats['warnings']}</b>\n\n"
        f"📋 <b>Pending reports (up to 5):</b>\n{pending_txt}\n\n"
        f"🔑 <b>Banned keywords:</b> {kw_txt}\n\n"
        "<b>Commands:</b>\n"
        "/ban &lt;user_id&gt; [reason]\n"
        "/unban &lt;user_id&gt;\n"
        "/warn &lt;user_id&gt; [reason]\n"
        "/broadcast &lt;message&gt;\n"
        "/setkeyword &lt;word&gt;\n"
        "/removekeyword &lt;word&gt;"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# ── /ban ─────────────────────────────────────────────────────────────────────

@admin_only
async def ban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /ban <user_id> [reason]")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    reason = " ".join(args[1:]) if len(args) > 1 else "No reason given"
    db.ban_user(target_id, reason)

    # Kick from any active chat
    user_row = db.get_user(target_id)
    if user_row and user_row["partner_id"]:
        partner_id = user_row["partner_id"]
        session_id = user_row["last_session"] or "N/A"
        db.set_partner(target_id, None, None)
        db.set_partner(partner_id, None, None)
        try:
            await context.bot.send_message(
                partner_id,
                "⚠️ Your partner was removed by an admin. Type /chat to find a new one."
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ User <code>{target_id}</code> banned.\nReason: {reason}",
        parse_mode=ParseMode.HTML
    )
    logger.info("Admin %s banned user %s (%s)", update.effective_user.id, target_id, reason)


# ── /unban ────────────────────────────────────────────────────────────────────

@admin_only
async def unban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    db.unban_user(target_id)
    await update.message.reply_text(
        f"✅ User <code>{target_id}</code> unbanned.",
        parse_mode=ParseMode.HTML
    )


# ── /warn ─────────────────────────────────────────────────────────────────────

@admin_only
async def warn_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /warn <user_id> [reason]")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    reason = " ".join(args[1:]) if len(args) > 1 else "No reason given"
    total = db.add_warning(target_id, update.effective_user.id, reason)

    # Auto-ban after 3 warnings
    if total >= 3:
        db.ban_user(target_id, "Auto-banned: 3 warnings reached")
        try:
            await context.bot.send_message(
                target_id,
                "⛔ You have been banned after 3 warnings."
            )
        except Exception:
            pass
        await update.message.reply_text(
            f"⛔ User <code>{target_id}</code> auto-banned after 3rd warning.",
            parse_mode=ParseMode.HTML
        )
    else:
        try:
            await context.bot.send_message(
                target_id,
                f"⚠️ You have received a warning ({total}/3).\nReason: {reason}"
            )
        except Exception:
            pass
        await update.message.reply_text(
            f"⚠️ Warning {total}/3 issued to <code>{target_id}</code>.\nReason: {reason}",
            parse_mode=ParseMode.HTML
        )


# ── /broadcast ────────────────────────────────────────────────────────────────

@admin_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    text = " ".join(context.args)
    users = db.get_all_users()
    sent = failed = 0

    for u in users:
        try:
            await context.bot.send_message(u["user_id"], f"📢 <b>Announcement:</b>\n\n{text}",
                                           parse_mode=ParseMode.HTML)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ Broadcast complete.\nSent: {sent} | Failed: {failed}")


# ── /setkeyword ───────────────────────────────────────────────────────────────

@admin_only
async def set_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /setkeyword <word>")
        return
    word = context.args[0].lower()
    db.add_keyword(word, update.effective_user.id)
    await update.message.reply_text(f"✅ Keyword <code>{word}</code> added.", parse_mode=ParseMode.HTML)


# ── /removekeyword ────────────────────────────────────────────────────────────

@admin_only
async def remove_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removekeyword <word>")
        return
    word = context.args[0].lower()
    db.remove_keyword(word)
    await update.message.reply_text(f"✅ Keyword <code>{word}</code> removed.", parse_mode=ParseMode.HTML)
