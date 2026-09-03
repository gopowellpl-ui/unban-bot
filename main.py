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
        await query.message.reply_text("Send Instagram username to monitor:\n(e.g. username)")
        context.user_data['action'] = 'add'

    elif data == "remove_username":
        await query.message.reply_text("Send Instagram username to remove from monitoring:")
        context.user_data['action'] = 'remove'

    elif data == "check_username":
        await query.message.reply_text("Send Instagram username to check status now:")
        context.user_data['action'] = 'check'

    elif data == "my_list":
        if not monitored_users:
            await query.message.reply_text("❌ No accounts in your monitoring list.")
        else:
            list_text = "📋 Monitored Accounts:\n" + "\n".join([f"• {u}" for u in monitored_users])
            await query.message.reply_text(list_text)

    elif data == "status":
        await query.message.reply_text(f"⚡ Bot Status: Active 24/7\n📊 Total Monitored: {len(monitored_users)}")

    elif data == "discord_webhook":
        await query.message.reply_text("⚙️ Discord webhook feature is currently disabled.")

async def handle_usernames_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id not in AUTHORIZED_IDS:
        return

    action = context.user_data.get('action')
    if not action:
        return

    if update.message and update.message.text:
        username = update.message.text.strip().replace('@', '')
        if not username:
            return

        if action == 'check':
            await update.message.reply_text(f"🔍 Checking status for {username}...")
            is_banned, followers = await check_instagram_user(username)
            if is_banned:
                await update.message.reply_text(f"⚠️ {username} is Banned.")
            else:
                await update.message.reply_text(f"✅ {username} is Active (Followers: {followers:,}).")
            context.user_data['action'] = None

        elif action == 'add':
            if username in monitored_users:
                await update.message.reply_text(f"⚠️ {username} is already in the list.")
            else:
                monitored_users.append(username)
                start_times[username] = datetime.now()
                banned_status[username] = True
                await update.message.reply_text(f"✅ Added {username} to monitoring list.")
            
            list_text = "📋 Monitored Accounts:\n" + "\n".join([f"• {u}" for u in monitored_users])
            await update.message.reply_text(list_text)
            context.user_data['action'] = None

        elif action == 'remove':
            if username in monitored_users:
                monitored_users.remove(username)
                start_times.pop(username, None)
                banned_status.pop(username, None)
                await update.message.reply_text(f"❌ Removed {username} from monitoring list.")
            else:
                await update.message.reply_text(f"⚠️ {username} not found in the list.")
            
            if monitored_users:
                list_text = "📋 Monitored Accounts:\n" + "\n".join([f"• {u}" for u in monitored_users])
                await update.message.reply_text(list_text)
            else:
                await update.message.reply_text("❌ No accounts in your monitoring list.")
            context.user_data['action'] = None

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_usernames_input))
    
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_loop(app))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
