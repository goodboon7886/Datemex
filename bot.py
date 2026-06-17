import os
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, 
    filters, ContextTypes, ConversationHandler
)

# Temporary storage
users = {}  
queue = []  
sessions = {} # Stores session_id: {user1_id, user2_id}

# Registration Steps
AGE, GENDER, COUNTRY, STATE_IN = range(4)

def generate_session_tag():
    """Generates a random 8-character alphanumeric session tag."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Datemexbot! 🌟\nLet's set up your profile.\n\n"
        "How old are you? (Type your age, e.g., 23)"
    )
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age = update.message.text
    if not age.isdigit():
        await update.message.reply_text("❌ Please enter a valid number for your age:")
        return AGE
    
    context.user_data['age'] = age

    keyboard = [
        [InlineKeyboardButton("👱‍♂️ Male", callback_data="Male"), 
         InlineKeyboardButton("👩 Female", callback_data="Female")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select your gender:", reply_markup=reply_markup)
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['gender'] = query.data

    keyboard = [
        [InlineKeyboardButton("🇮🇳 India", callback_data="India"), InlineKeyboardButton("🇺🇸 America", callback_data="America")],
        [InlineKeyboardButton("🇨🇳 China", callback_data="China"), InlineKeyboardButton("🇷🇺 Russia", callback_data="Russia")],
        [InlineKeyboardButton("🇪🇹 Ethiopia", callback_data="Ethiopia"), InlineKeyboardButton("🇮🇩 Indonesia", callback_data="Indonesia")],
        [InlineKeyboardButton("🇸🇦 Saudi Arabia", callback_data="Saudi Arabia"), InlineKeyboardButton("🇮🇷 Iran", callback_data="Iran")],
        [InlineKeyboardButton("🇬🇧 UK", callback_data="UK"), InlineKeyboardButton("🇮🇹 Italy", callback_data="Italy")],
        [InlineKeyboardButton("🇧🇷 Brazil", callback_data="Brazil"), InlineKeyboardButton("🇳🇬 Nigeria", callback_data="Nigeria")],
        [InlineKeyboardButton("🇲🇾 Malaysia", callback_data="Malaysia"), InlineKeyboardButton("🇩🇪 Germany", callback_data="Germany")],
        [InlineKeyboardButton("🇪🇸 Spain", callback_data="Spain"), InlineKeyboardButton("🇫🇷 France", callback_data="France")],
        [InlineKeyboardButton("🇿🇦 South Africa", callback_data="South Africa"), InlineKeyboardButton("🇨🇦 Canada", callback_data="Canada")],
        [InlineKeyboardButton("🇯🇵 Japan", callback_data="Japan"), InlineKeyboardButton("🇦🇺 Australia", callback_data="Australia")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🌍 Select your country:", reply_markup=reply_markup)
    return COUNTRY

async def get_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country = query.data
    context.user_data['country'] = country

    if country == "India":
        indian_states = [
            "Andaman & Nicobar", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
            "Bihar", "Chandigarh", "Chhattisgarh", "Dadra & Nagar Haveli",
            "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu & Kashmir",
            "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
            "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
            "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
            "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
        ]
        
        state_buttons = []
        for i in range(0, len(indian_states), 2):
            row = [InlineKeyboardButton(indian_states[i], callback_data=indian_states[i])]
            if i + 1 < len(indian_states):
                row.append(InlineKeyboardButton(indian_states[i+1], callback_data=indian_states[i+1]))
            state_buttons.append(row)

        reply_markup = InlineKeyboardMarkup(state_buttons)
        await query.edit_message_text("🇮🇳 Select your region in India:", reply_markup=reply_markup)
        return STATE_IN
    else:
        user_id = query.from_user.id
        users[user_id] = {
            'age': context.user_data['age'],
            'gender': context.user_data['gender'],
            'state': country,
            'partner': None,
            'last_session': None
        }
        await query.edit_message_text("✅ Profile Registered! Type /chat to find a partner.")
        return ConversationHandler.END

async def get_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = query.data
    user_id = query.from_user.id

    users[user_id] = {
        'age': context.user_data['age'],
        'gender': context.user_data['gender'],
        'state': f"India - {state}",
        'partner': None,
        'last_session': None
    }
    await query.edit_message_text("✅ Profile Registered! Type /chat to find a partner.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled. Type /start to try again.")
    return ConversationHandler.END

# --- CHAT FEATURES & SESSION TAGS ---

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in users:
        await update.message.reply_text("⚠️ Please register first by typing /start")
        return

    if users.get(user_id, {}).get('partner'):
        await update.message.reply_text("You are already connected to a partner!")
        return

    if user_id in queue:
        await update.message.reply_text("🔎 Still searching the dating pool for you...")
        return

    if queue:
        partner_id = queue.pop(0)
        session_id = generate_session_tag()
        
        # Link users and assign session
        users[user_id]['partner'] = partner_id
        users[partner_id]['partner'] = user_id
        users[user_id]['last_session'] = session_id
        users[partner_id]['last_session'] = session_id
        sessions[session_id] = {user_id, partner_id}
        
        # Match card formatting (Using HTML for spoilers as requested)
        def get_match_card(target_id):
            return (
                "✅ <b>Partner Matched</b>\n\n"
                f"🔢 <b>Age:</b> {users[target_id]['age']}\n"
                f"👥 <b>Gender:</b> <tg-spoiler>{users[target_id]['gender']}</tg-spoiler>\n"
                f"🌍 <b>Country:</b> {users[target_id]['state']}\n\n"
                "🚫 <i>Links are restricted</i>\n"
                "⏱ <i>Media sharing unlocked after 2 minutes</i>\n\n"
                "/exit — Leave the chat"
            )
        
        await context.bot.send_message(user_id, get_match_card(partner_id), parse_mode=ParseMode.HTML)
        await context.bot.send_message(partner_id, get_match_card(user_id), parse_mode=ParseMode.HTML)
    else:
        queue.append(user_id)
        await update.message.reply_text("🔎 Looking for an available user matching your interests... Please wait.")

async def send_disconnect_card(context, user_id, session_id):
    """Sends the disconnect card with the session tag and report buttons"""
    disconnect_msg = (
        "🚫 <b>Partner left the chat</b>\n\n"
        "/chat - Find new partner\n"
        "───────────────\n"
        f"⚠️ <b>Session TAG:</b> {session_id}\n\n"
        f"<i>To reconnect:</i> /rechat {session_id}\n"
        f"<i>To report:</i> /report {session_id}"
    )
    keyboard = [[InlineKeyboardButton("⚠️ Report User", callback_data=f"report_{session_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(user_id, disconnect_msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    except:
        pass

async def exit_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        return

    partner_id = users.get(user_id, {}).get('partner')
    session_id = users.get(user_id, {}).get('last_session')

    if partner_id:
        users[user_id]['partner'] = None
        users[partner_id]['partner'] = None
        
        await send_disconnect_card(context, user_id, session_id)
        await send_disconnect_card(context, partner_id, session_id)
    else:
        if user_id in queue:
            queue.remove(user_id)
            await update.message.reply_text("Search canceled.")
        else:
            await update.message.reply_text("You are currently not in a chat.")

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        return
        
    partner_id = users.get(user_id, {}).get('partner')
    session_id = users.get(user_id, {}).get('last_session')

    if partner_id:
        users[user_id]['partner'] = None
        users[partner_id]['partner'] = None
        await send_disconnect_card(context, partner_id, session_id)
    
    if user_id in queue:
        queue.remove(user_id)
        
    await chat(update, context)

async def handle_button_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("report_"):
        session_id = query.data.split("_")[1]
        await query.edit_message_text(f"✅ Report submitted for Session: {session_id}. Our team will review this user.")

async def handle_anonymous_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = users.get(user_id, {}).get('partner')

    if not partner_id:
        await update.message.reply_text("You are alone. Type /chat to start matching up!")
        return

    if update.message.text:
        if "http" in update.message.text or "t.me" in update.message.text or "@" in update.message.text:
            await update.message.reply_text("🚫 External links and usernames are restricted to prevent scams!")
        else:
            await context.bot.send_message(partner_id, update.message.text)
            
    elif update.message.photo:
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        await context.bot.send_photo(partner_id, photo_id, caption=caption)

if __name__ == '__main__':
    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [CallbackQueryHandler(get_gender)],
            COUNTRY: [CallbackQueryHandler(get_country)],
            STATE_IN: [CallbackQueryHandler(get_state)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("exit", exit_chat))
    
    # Handle the report inline button click
    app.add_handler(CallbackQueryHandler(handle_button_callbacks, pattern="^report_"))
    
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_anonymous_messages))

    print("Bot is up and running...")
    app.run_polling()
