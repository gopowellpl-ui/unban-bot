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
                    followers = user_data.get("edge_followed_by", {}).get("count", 0)
                    return False, followers
                elif response.status == 404:
                    return True, 0
                else:
                    return None, 0
    except Exception:
        return None, 0

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
                total_seconds = int(duration.total_seconds())
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                minutes = (total_seconds % 3600) // 60
                hours_decimal = round(total_seconds / 3600, 2)
                
                duration_text = f"{days} days {hours} hours {minutes} minutes ({hours_decimal} hours)"

                message_text = (
                    f"Unbanned\n\n"
                    f"Username: @{username}\n"
                    f"Link: https://instagram.com/{username}\n"
                    f"Followers : {followers:,}\n\n"
                    f"Started: {start_time_str}\n"
                    f"Unbanned: {unban_time_str}\n"
                    f"Monitored for: {duration_text}\n\n"
                    f"This account is now active."
                )

                banned_status[username] = False
                media_url = "https://files.catbox.moe/0kb2pb.mp4"
                
                for chat_id in application.bot_data.get("chat_ids", set()):
                    try:
                        await application.bot.send_animation(
                            chat_id=chat_id,
                            animation=media_url,
                            caption=message_text
                        )
                    except Exception:
                        pass

            elif is_banned is True:
                banned_status[username] = True

        await asyncio.sleep(30)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        return

    if update.effective_chat:
        chat_ids = context.application.bot_data.setdefault("chat_ids", set())
        chat_ids.add(update.effective_chat.id)

    welcome_text = (
        "Instagram Unban Monitor by\n"
        "@vvvssvv\n\n"
        "Track banned accounts and get notified the moment they come back.\n\n"
        "Currently scanning every 30s."
    )
    media_url = "https://files.catbox.moe/0kb2pb.mp4"

    try:
        if update.message:
            await update.message.reply_animation(
                animation=media_url,
                caption=welcome_text,
                reply_markup=get_main_keyboard()
            )
    except Exception:
        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        await update.callback_query.answer("Your subscription has expired", show_alert=True)
        return

    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_username":
        text = (
            "Add usernames to monitor\n\n"
            "Send Instagram usernames in either way:\n"
            "• Type them here (space or newline separated)\n"
            "• Upload a .txt file (one username per line)\n\n"
            "Example:\n"
            "user1\n"
            "user2\n"
            "@user3\n\n"
            "Banned accounts will be added to your watch list.\n"
            "You will get a notification when any of them is unbanned.\n\n"
            "Your limit: 0/10 used — 10 free slot(s) left.\n\n"
            "Send /cancel to abort."
        )
        await query.message.reply_text(text)
        context.user_data['action'] = 'add'

    elif data == "remove_username":
        text = (
            "Remove usernames\n\n"
            "Send the usernames you want to remove:\n"
            "• Type them here (space or newline separated)\n"
            "• Or upload a .txt file (one per line)\n\n"
            "Example: user1 user2\n\n"
            "Send /cancel to abort."
        )
        await query.message.reply_text(text)
        context.user_data['action'] = 'remove'

    elif data == "check_username":
        text = (
            "Check one username\n\n"
            "Send a single Instagram username to see its status right now.\n\n"
            "Example: user1\n\n"
            "This is a one-time check — it does not add the account to monitoring.\n\n"
            "Send /cancel to abort."
        )
        await query.message.reply_text(text)
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
            "Track banned accounts and get notified the moment they come back.\n\n"
            "Currently scanning every 30s."
        )
        await query.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

    elif data == "status":
        await query.message.reply_text(f"⚡ Bot Status: Active 24/7\n🔍 Interval: 30s\n📊 Total Monitored: {len(monitored_users)}")

    elif data == "discord_webhook":
        await query.message.reply_text("⚙️ Discord webhook feature is currently disabled.")

    elif data == "noop":
        pass

async def handle_usernames_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        return

    action = context.user_data.get('action')
    if not action:
        return

    if update.message and update.message.text and update.message.text.strip() == "/cancel":
        context.user_data['action'] = None
        await update.message.reply_text("Operation cancelled.", reply_markup=get_main_keyboard())
        return

    usernames = []
    
    if update.message and update.message.document:
        doc = update.message.document
        file = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()
        content = file_bytes.decode('utf-8', errors='ignore')
        usernames = [line.strip().replace('@', '') for line in content.splitlines() if line.strip()]
    elif update.message and update.message.text:
        text = update.message.text
        usernames = [u.strip().replace('@', '') for u in text.replace(',', ' ').split() if u.strip()]

    if not usernames:
        return

    if action == 'check':
        username = usernames[0]
        await update.message.reply_text(f"Checking @{username}...")
        is_banned, followers = await check_instagram_user(username)
        
        if is_banned:
            status_text = (
                f"@{username}\n\n"
                f"Status: Banned\n\n"
                f"This account looks banned right now.\n"
                f"Use Add if you want it on the monitoring list."
            )
        else:
            status_text = f"@{username}\n\nStatus: Active (Followers: {followers:,})"
            
        await update.message.reply_text(status_text)
        context.user_data['action'] = None

    elif action == 'add':
        total_checked = len(usernames)
        await update.message.reply_text(f"Check finished\n\nChecked: {total_checked} username(s)\nSending results...")
        
        banned_added = []
        for username in usernames:
            is_banned, _ = await check_instagram_user(username)
            if is_banned:
                if username not in monitored_users:
                    monitored_users.append(username)
                    start_times[username] = datetime.now()
                    banned_status[username] = True
                    banned_added.append(f"@{username}")

        await update.message.reply_text(f"Done — checked {total_checked} username(s)")

        if banned_added:
            file_path = "added_banned.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(banned_added))
            with open(file_path, "rb") as f:
                await update.message.reply_document(document=f)
            if os.path.exists(file_path):
                os.remove(file_path)

        added_count = len(banned_added)
        success_msg = (
            f"✅ Added to monitoring: {added_count}\n\n"
            f"These accounts are banned and now on your watch list.\n"
            f"When any of them gets unbanned, you will get a notification automatically."
        )
        await update.message.reply_text(success_msg)
        context.user_data['action'] = None

    elif action == 'remove':
        removed_count = 0
        removed_names = []
        for username in usernames:
            if username in monitored_users:
                monitored_users.remove(username)
                start_times.pop(username, None)
                banned_status.pop(username, None)
                removed_names.append(f"- @{username}")
                removed_count += 1

        removed_str = "\n".join(removed_names) if removed_names else ""
        await update.message.reply_text(f"Removed: {removed_count}\n{removed_str}")
        context.user_data['action'] = None

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler((filters.TEXT | filters.Document.ALL) & ~filters.COMMAND, handle_usernames_input))
    
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_loop(app))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
