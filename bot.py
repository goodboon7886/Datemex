import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, 
    filters, ContextTypes, ConversationHandler
)

# Temporary storage
users = {}  
queue = []  

# Registration Steps
AGE, GENDER, COUNTRY, STATE_IN = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ask for Age
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

    # Ask for Gender with Buttons
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

    # Ask for Country with 20 Flag Buttons
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
        # Ask for State if India is chosen
        indian_states = [
            "Andaman & Nicobar", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
            "Bihar", "Chandigarh", "Chhattisgarh", "Dadra & Nagar Haveli",
            "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu & Kashmir",
            "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
            "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
            "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
            "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
        ]
        
        # Format buttons into two columns
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
        # Save profile for non-India countries
        user_id = query.from_user.id
        users[user_id] = {
            'age': context.user_data['age'],
            'gender': context.user_data['gender'],
            'state': country,
            'partner': None
        }
        await query.edit_message_text(
            f"✅ Profile Registered!\n\n"
            f"🔢 Age: {users[user_id]['age']}\n"
            f"👥 Gender: {users[user_id]['gender']}\n"
            f"🌍 Location: {users[user_id]['state']}\n\n"
            f"Type /chat to instantly look for a partner!"
        )
        return ConversationHandler.END

async def get_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = query.data
    user_id = query.from_user.id

    # Save profile for India + State
    users[user_id] = {
        'age': context.user_data['age'],
        'gender': context.user_data['gender'],
        'state': f"India - {state}",
        'partner': None
    }
    await query.edit_message_text(
        f"✅ Profile Registered!\n\n"
        f"🔢 Age: {users[user_id]['age']}\n"
        f"👥 Gender: {users[user_id]['gender']}\n"
        f"🌍 Location: {users[user_id]['state']}\n\n"
        f"Type /chat to instantly look for a partner!"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled. Type /start to try again.")
    return ConversationHandler.END

# --- CHAT FEATURES ---

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
        users[user_id]['partner'] = partner_id
        users[partner_id]['partner'] = user_id
        
        match_card = (
            "✅ Partner Matched!\n\n"
            "🔢 Age: {age}\n"
            "👥 Gender: {gender}\n"
            "🌍 Location: {state}\n\n"
            "🚫 Links are blocked for safety.\n"
            "📸 You can now text and send pictures anonymously!\n\n"
            "/next — Skip to a new person\n"
            "/exit — Stop chatting"
        )
        
        await context.bot.send_message(user_id, match_card.format(**users[partner_id]))
        await context.bot.send_message(partner_id, match_card.format(**users[user_id]))
    else:
        queue.append(user_id)
        await update.message.reply_text("🔎 Looking for an available user matching your interests... Please wait.")

async def exit_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = users.get(user_id, {}).get('partner')

    if partner_id:
        users[user_id]['partner'] = None
        users[partner_id]['partner'] = None
        await update.message.reply_text("You disconnected from the chat.")
        await context.bot.send_message(partner_id, "⚠️ Your partner left the room. Type /chat to find someone new.")
    else:
        if user_id in queue:
            queue.remove(user_id)
            await update.message.reply_text("Search canceled.")
        else:
            await update.message.reply_text("You are currently not in a chat.")

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = users.get(user_id, {}).get('partner')

    if partner_id:
        users[user_id]['partner'] = None
        users[partner_id]['partner'] = None
        await context.bot.send_message(partner_id, "⚠️ Your partner skipped the chat. Type /chat to find someone new.")
    
    if user_id in queue:
        queue.remove(user_id)
        
    await update.message.reply_text("Skipping forward...")
    await chat(update, context)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = users.get(user_id, {}).get('partner')
    
    if partner_id:
        await update.message.reply_text("🚨 User reported for bad behavior. Finding you a new chat room...")
        await next_chat(update, context)
    else:
        await update.message.reply_text("You can only report active partners.")

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

    # Set up the Registration flow
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
    app.add_handler(CommandHandler("report", report))
    
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_anonymous_messages))

    print("Bot is up and running...")
    app.run_polling()
