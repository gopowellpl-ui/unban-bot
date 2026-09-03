import asyncio
import logging
import os
import aiohttp
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
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
    try:
        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())
    except Exception:
        pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        return

    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_username":
        await query.message.reply_text(
            "Send Instagram usernames in either way:\n"
            "- Send usernames line by line (one per message)\n"
            "- Or upload a .txt file (one per line)\n\n"
            "Send /cancel to abort."
        )
        context.user_data['action'] = 'add'

    elif data == "remove_username":
        await query.message.reply_text(
            "Send the username you want to remove:\n\nSend /cancel to abort."
        )
        context.user_data['action'] = 'remove'

    elif data == "check_username":
        await query.message.reply_text("Send Instagram username to check status now:")
        context.user_data['action'] = 'check'

    elif data == "my_list":
        if not monitored_users:
            await query.message.reply_text("❌ No accounts in your watch list.")
        else:
            banned_list = [u for u in monitored_users if banned_status.get(u, True)]
            active_list = [u for u in monitored_users if not banned_status.get(u, True)]
            
            list_text = f"Your watch list ({len(monitored_users)}) · page 1/1\n\n"
            list_text += "Banned\n"
            if banned_list:
                for u in banned_list:
                    list_text += f"- @{u}\n"
            else:
                list_text += "- None\n"
                
            list_text += "\nUnbanned\n"
            if active_list:
                for u in active_list:
                    list_text += f"- @{u}\n"
            else:
                list_text += "- None"

            keyboard = [
                [InlineKeyboardButton("1/1", callback_data="noop")],
                [InlineKeyboardButton("Download .txt", callback_data="download_txt")],
                [InlineKeyboardButton("Home", callback_data="home_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(list_text, reply_markup=reply_markup)

    elif data == "download_txt":
        if monitored_users:
            file_content = "\n".join(monitored_users)
            file_path = "my_watch_list.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)
            
            with open(file_path, "rb") as f:
                await query.message.reply_document(document=InputFile(f, filename="my_watch_list.txt"))
            try:
                os.remove(file_path)
            except Exception:
                pass
        else:
            await query.message.reply_text("❌ No accounts to export.")

    elif data == "home_menu":
        welcome_text = (
            "Instagram Unban Monitor by\n"
            "@vvvssvv\n\n"
            "Track banned accounts and get notified the moment they come back.\n\n"
            "Currently scanning every 30s."
        )
        await query.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

    elif data == "status":
        await query.message.reply_text(f"⚡ Bot Status: Active 24/7\n📊 Total Monitored: {len(monitored_users)}")

    elif data == "discord_webhook":
        await query.message.reply_text("⚙️ Discord webhook feature is currently disabled.")

async def handle_usernames_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        return

    if update.message and update.message.text and update.message.text.strip() == "/cancel":
        context.user_data['action'] = None
        await update.message.reply_text("Cancelled.", reply_markup=get_main_keyboard())
        return

    action = context.user_data.get('action')
    if not action:
        return

    # معالجة الملفات المرفوعة (.txt)
    usernames_to_process = []
    if update.message and update.message.document:
        doc = update.message.document
        if doc.file_name and doc.file_name.endswith('.txt'):
            file = await context.bot.get_file(doc.file_id)
            file_bytes = await file.download_as_bytearray()
            text_content = file_bytes.decode('utf-8', errors='ignore')
            usernames_to_process = [line.strip().replace('@', '') for line in text_content.splitlines() if line.strip()]

    # معالجة النصوص المرسلة
    elif update.message and update.message.text:
        text = update.message.text.strip()
        usernames_to_process = [line.strip().replace('@', '') for line in text.splitlines() if line.strip()]

    if not usernames_to_process:
        return

    if action == 'check':
        username = usernames_to_process[0]
        await update.message.reply_text(f"🔍 Checking status for {username}...")
        is_banned, followers = await check_instagram_user(username)
        if is_banned:
            await update.message.reply_text(f"⚠️ {username} is Banned.")
        else:
            await update.message.reply_text(f"✅ {username} is Active (Followers: {followers:,}).")
        context.user_data['action'] = None

    elif action == 'add':
        await update.message.reply_text("Check finished")
        await update.message.reply_text(f"Checked: {len(usernames_to_process)} username(s)\nSending results...")
        
        added_count = 0
        added_usernames = []
        for username in usernames_to_process:
            if username not in monitored_users:
                monitored_users.append(username)
                start_times[username] = datetime.now()
                banned_status[username] = True
                added_usernames.append(username)
                added_count += 1

        await update.message.reply_text(f"Done — checked {len(usernames_to_process)} username(s)")

        if added_usernames:
            file_path = "added_banned.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(added_usernames))
            
            with open(file_path, "rb") as f:
                await update.message.reply_document(document=InputFile(f, filename="added_banned.txt"))
            try:
                os.remove(file_path)
            except Exception:
                pass

        success_msg = (
            f"✅ Added to monitoring: {added_count}\n\n"
            "These accounts are banned and now on your watch list.\n"
            "When any of them gets unbanned, you will get a notification automatically."
        )
        await update.message.reply_text(success_msg)
        context.user_data['action'] = None

    elif action == 'remove':
        username = usernames_to_process[0]
        if username in monitored_users:
            monitored_users.remove(username)
            start_times.pop(username, None)
            banned_status.pop(username, None)
            await update.message.reply_text(f"❌ Removed {username} from monitoring list.")
        else:
            await update.message.reply_text(f"⚠️ {username} not found in the list.")
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
