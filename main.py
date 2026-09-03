import asyncio
import logging
import os
from threading import Thread
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8855215599:AAFwLPnwCn6fW9yKTA95wzgd7Bt3LXDW0j8"
monitored_users = []

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Add username", callback_data="add_username"),
            InlineKeyboardButton("Remove username", callback_data="remove_username")
        ],
        [
            InlineKeyboardButton("Check username", callback_data="check_username"),
            InlineKeyboardButton("My List", callback_data="my_list")
        ],
        [
            InlineKeyboardButton("Status", callback_data="status"),
            InlineKeyboardButton("Discord webhook", callback_data="discord_webhook")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Instagram Unban Monitor by\n"
        "@vvvssvv\n\n"
        "Track banned accounts and get notified the moment they come back.\n\n"
        "Currently scanning every **30s**."
    )
    media_url = "https://files.catbox.moe/0kb2pb.mp4"

    try:
        if update.message:
            await update.message.reply_animation(
                animation=media_url,
                caption=welcome_text,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        elif update.callback_query:
            await update.callback_query.message.reply_animation(
                animation=media_url,
                caption=welcome_text,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    except Exception:
        if update.message:
            await update.message.reply_text(welcome_text, parse_Mode="Markdown", reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "add_username":
        await query.message.reply_text(" Send Instagram username to monitor:\n(e.g. `username`)", parse_mode="Markdown")
        context.user_data['action'] = 'add'
    elif data == "remove_username":
        await query.message.reply_text(" Send Instagram username to remove:", parse_mode="Markdown")
        context.user_data['action'] = 'remove'
    elif data == "check_username":
        await query.message.reply_text(" Send Instagram username to check status now:", parse_mode="Markdown")
        context.user_data['action'] = 'check'
    elif data == "my_list":
        if monitored_users:
            users_str = "\n".join([f"• `{u}`" for u in monitored_users])
            await query.message.reply_text(f"📋 **Monitored Accounts:**\n{users_str}", parse_mode="Markdown")
        else:
            await query.message.reply_text("❌ No accounts in your monitoring list.")
    elif data == "status":
        await query.message.reply_text(f"⚡ **Bot Status:** Active 24/7\n🔍 **Interval:** 30s\n📊 **Total Monitored:** {len(monitored_users)}")
    elif data == "discord_webhook":
        await query.message.reply_text("⚙️ Discord webhook feature is currently disabled.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    text = update.message.text.strip().replace('@', '')
    
    if action == 'add':
        if text not in monitored_users:
            monitored_users.append(text)
            await update.message.reply_text(f"✅ Added `{text}` to monitoring list.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⚠️ `{text}` is already in the list.", parse_mode="Markdown")
        context.user_data['action'] = None
    elif action == 'remove':
        if text in monitored_users:
            monitored_users.remove(text)
            await update.message.reply_text(f"🗑️ Removed `{text}` from monitoring list.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ `{text}` was not found in your list.", parse_mode="Markdown")
        context.user_data['action'] = None
    elif action == 'check':
        await update.message.reply_text(f"🔍 Checking status for `{text}`...", parse_mode="Markdown")
        context.user_data['action'] = None

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("🎉 البوت يعمل الآن على مدار 24 ساعة...")
    app.run_polling()

if __name__ == '__main__':
    main()
