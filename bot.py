import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Temporary storage for profiles and users waiting
users = {}  
queue = []  

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {'age': 'N/A', 'gender': 'N/A', 'state': 'N/A', 'partner': None}
    await update.message.reply_text(
        "Welcome to Datemexbot! 🌟\n\n"
        "Find your Sugar Daddy, Sugar Baby, Boyfriend, or Girlfriend completely anonymously.\n\n"
        "Step 1: Save your profile using this format:\n"
        "/register Age Gender Location\n\n"
        "Example:\n"
        "/register 24 Female NewYork"
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        age = context.args[0]
        gender = context.args[1]
        state = context.args[2]
        
        users[user_id] = {'age': age, 'gender': gender, 'state': state, 'partner': None}
        await update.message.reply_text(
            f"✅ Profile Registered!\n\n"
            f"🔢 Age: {age}\n"
            f"👥 Gender: {gender}\n"
            f"🌍 Location: {state}\n\n"
            f"Type /chat to instantly look for a partner!"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Please use the correct layout:\n/register Age Gender Location")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
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

    # Text Forwarding + Scam/Link Filter
    if update.message.text:
        if "http" in update.message.text or "t.me" in update.message.text or "@" in update.message.text:
            await update.message.reply_text("🚫 External links and usernames are restricted to prevent scams!")
        else:
            await context.bot.send_message(partner_id, update.message.text)
            
    # Picture Forwarding
    elif update.message.photo:
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        await context.bot.send_photo(partner_id, photo_id, caption=caption)

if __name__ == '__main__':
    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("exit", exit_chat))
    app.add_handler(CommandHandler("report", report))
    
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_anonymous_messages))

    print("Bot is up and running...")
    app.run_polling()
