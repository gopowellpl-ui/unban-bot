import asyncio
import logging
import os
import aiohttp
from datetime import datetime
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
AUTHORIZED_IDS = [2088240041, 385080721]

monitored_users = []
banned_status = {}
start_times = {}

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Add usernames", callback_data="add_username"),
            InlineKeyboardButton("Remove username", callback_data="remove_username")
        ],
        [
            InlineKeyboardButton("Check usernames", callback_data="check_username"),
            InlineKeyboardButton("My List", callback_data="my_list")
        ],
        [
            InlineKeyboardButton("Status", callback_data="status"),
            InlineKeyboardButton("Discord webhook", callback_data="discord_webhook")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_mylist_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("1/1", callback_data="noop"),
            InlineKeyboardButton("Download .txt", callback_data="download_mylist")
        ],
        [
            InlineKeyboardButton("Home", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_instagram_user(username):
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    user_data = data.get("graphql", {}).get("user", {})
                    is_banned = False
                    followers = user_data.get("edge_followed_by", {}).get("count", "N/A")
                    return is_banned, followers
                elif response.status == 404:
                    return True, 0
                else:
                    return None, "N/A"
    except Exception:
        return None, "N/A"

async def monitor_loop(application: Application):
    await asyncio.sleep(5)
    while True:
        for username in list(monitored_users):
            if username not in start_times:
                start_times[username] = datetime.now()
                banned_status[username] = True

            is_banned, followers = await check_instagram_user(username)
            
            if is_banned is False and banned_status.get(username, True) is True:
                unban_time = datetime.now()
                start_time_str = start_times[username].strftime("%Y-%m-%d %H:%M:%S")
                unban_time_str = unban_time.strftime("%Y-%m-%d %H:%M:%S")
                duration = unban_time - start_times[username]
                duration_text = str(duration).split('.')[0]

                message_text = (
                    f"**Username**: `{username}`\n"
                    f"**Link**: https://instagram.com/{username}\n"
                    f"**Followers**: `{followers}`\n"
                    f"**Start Time**: `{start_time_str}`\n"
                    f"**Unban Time**: `{unban_time_str}`\n"
                    f"**Duration**: `{duration_text}`\n\n"
                    f"This account is now active."
                )

                banned_status[username] = False
                for chat_id in application.bot_data.get("chat_ids", set()):
                    try:
                        await application.bot.send_message(chat_id=chat_id, text=message_text, parse_mode="Markdown")
                    except Exception:
                        pass

            elif is_banned is True:
                banned_status[username] = True

        await asyncio.sleep(30)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        if update.message:
            await update.message.reply_text("Your subscription has expired")
        return

    if update.effective_chat:
        chat_ids = context.application.bot_data.setdefault("chat_ids", set())
        chat_ids.add(update.effective_chat.id)

    welcome_text = (
        "Instagram Unban Monitor by\n"
        "@vvvssvv\n\n"
        "Send Instagram usernames in either way or upload a text file to monitor.\n\n"
        "Send /cancel to abort."
    )
    
    try:
        if update.message:
            await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
        elif update.callback_query:
            await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    except Exception:
        pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        await update.callback_query.answer("Your subscription has expired", show_alert=True)
        return

    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "add_username":
        await query.message.reply_text("Send Instagram usernames to monitor (one per line, or upload a `.txt` file):\n\nSend /cancel to abort.", parse_mode="Markdown")
        context.user_data['action'] = 'add'
    elif data == "remove_username":
        await query.message.reply_text("Send Instagram username to remove:", parse_mode="Markdown")
        context.user_data['action'] = 'remove'
    elif data == "check_username":
        await query.message.reply_text("Send Instagram username or upload a file to check status now:", parse_mode="Markdown")
        context.user_data['action'] = 'check'
    elif data == "my_list":
        banned_list_text = [f"- @{u}" for u in monitored_users if banned_status.get(u, True)]
        unbanned_list_text = [f"- @{u}" for u in monitored_users if not banned_status.get(u, True)]
        
        banned_str = "\n".join(banned_list_text) if banned_list_text else "None"
        unbanned_str = "\n".join(unbanned_list_text) if unbanned_list_text else "None"
        
        list_text = (
            f"Your watch list ({len(monitored_users)}) · page 1/1\n\n"
            f"Banned\n{banned_str}\n\n"
            f"Unbanned\n{unbanned_str}"
        )
        await query.message.reply_text(list_text, reply_markup=get_mylist_keyboard())
    elif data == "download_mylist":
        file_path = "my_watch_list.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join([f"@{u}" for u in monitored_users]))
        with open(file_path, "rb") as f:
            await query.message.reply_document(document=f)
        if os.path.exists(file_path):
            os.remove(file_path)
    elif data == "home":
        welcome_text = (
            "Instagram Unban Monitor by\n"
            "@vvvssvv\n\n"
            "Send Instagram usernames in either way or upload a text file to monitor.\n\n"
            "Send /cancel to abort."
        )
        await query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    elif data == "status":
        await query.message.reply_text(f"⚡ **Bot Status:** Active 24/7\n🔍 **Interval:** 30s\n📊 **Total Monitored:** {len(monitored_users)}")
    elif data == "discord_webhook":
        await query.message.reply_text("⚙️ Discord webhook feature is currently disabled.")
    elif data == "noop":
        pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        return
    context.user_data['action'] = None
    await update.message.reply_text("❌ Operation cancelled.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        return

    action = context.user_data.get('action')
    if not action:
        return

    if update.message.document:
        document = update.message.document
        if document.file_name.endswith('.txt'):
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            lines = file_bytes.decode('utf-8').splitlines()
            
            added_count = 0
            banned_list = []
            
            for line in lines:
                username = line.strip().replace('@', '')
                if username:
                    if action == 'add':
                        if username not in monitored_users:
                            monitored_users.append(username)
                            start_times[username] = datetime.now()
                            banned_status[username] = True
                            added_count += 1
                    elif action == 'check':
                        is_banned, _ = await check_instagram_user(username)
                        if is_banned:
                            banned_list.append(username)

            if action == 'add':
                await update.message.reply_text(f"✅ Added to monitoring: {added_count}\n\nThese accounts are on your watch list. When any of them gets unbanned, you will get a notification automatically.", parse_mode="Markdown")
            elif action == 'check':
                file_path = "added_banned.txt"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(banned_list))
                with open(file_path, "rb") as f:
                    await update.message.reply_document(document=f, caption=f"Check finished\nChecked: {len(lines)} username(s)\nBanned found: {len(banned_list)}")
                if os.path.exists(file_path):
                    os.remove(file_path)

            context.user_data['action'] = None
            return

    if not update.message.text:
        return

    text = update.message.text.strip().replace('@', '')

    if action == 'add':
        usernames = [u.strip().replace('@', '') for u in text.splitlines() if u.strip()]
        added = 0
        for u in usernames:
            if u not in monitored_users:
                monitored_users.append(u)
                start_times[u] = datetime.now()
                banned_status[u] = True
                added += 1
        await update.message.reply_text(f"✅ Added to monitoring: {added}\n\nThese accounts are banned and now on your watch list.\nWhen any of them gets unbanned, you will get a notification automatically.", parse_mode="Markdown")
        context.user_data['action'] = None
    elif action == 'remove':
        if text in monitored_users:
            monitored_users.remove(text)
            start_times.pop(text, None)
            banned_status.pop(text, None)
            await update.message.reply_text(f"🗑️ Removed `{text}` from monitoring list.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ `{text}` was not found in your list.", parse_mode="Markdown")
        context.user_data['action'] = None
    elif action == 'check':
        await update.message.reply_text(f"🔍 Checking status for `{text}`...", parse_mode="Markdown")
        is_banned, followers = await check_instagram_user(text)
        status_msg = "🔴 Banned / Not Found" if is_banned else f"🟢 Active (Followers: {followers})"
        await update.message.reply_text(f"Status for `{text}`: {status_msg}", parse_mode="Markdown")
        context.user_data['action'] = None

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, message_handler))
    
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_loop(app))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
