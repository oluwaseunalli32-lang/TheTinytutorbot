import asyncio
import logging
import random
import os
import sqlite3
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set!")

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = c.fetchall()
    conn.close()
    return [row[0] for row in users]

# Lessons Data
LESSONS = [
    {"topic": "History", "title": "The Battle of Hastings (1066)", "content": "William the Conqueror... "},
    # ... add 10 more
]

def get_daily_lesson():
    return random.choice(LESSONS)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    lesson = get_daily_lesson()
    await update.message.reply_text(f"Welcome to TinyTutor! 🎓\n\nHere's your first 5-min lesson:\n\n*{lesson['title']}*\n{lesson['content']}\n\nI'll send you a new lesson every day at 9 AM UTC!", parse_mode='Markdown')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    remove_user(user_id)
    await update.message.reply_text("You have been unsubscribed. Send /start to resubscribe.")

async def send_daily_lessons(app):
    users = get_all_users()
    if not users:
        logger.info("No users to send lessons to.")
        return
    lesson = get_daily_lesson()
    text = f"📚 *Daily TinyTutor Lesson*\n\n*Topic: {lesson['topic']}*\n*{lesson['title']}*\n\n{lesson['content']}\n\nSee you tomorrow! 🧠"
    for user_id in users:
        try:
            await app.bot.send_message(chat_id=user_id, text=text, parse_mode='Markdown')
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")

async def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_lessons, 'cron', hour=9, minute=0, args=[app])
    scheduler.start()
    logger.info("Scheduler started. Bot is polling...")

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
