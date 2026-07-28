import asyncio
import logging
import random
import os
import sqlite3
import signal
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------- LOGGING ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- CONFIG ----------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set in environment variables!")

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_user(user_id: int):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# ---------- LESSON DATABASE ----------
LESSONS = [
    {
        "topic": "History",
        "title": "The Battle of Hastings (1066)",
        "content": "William the Conqueror defeated King Harold II, changing England forever. It marked the end of Anglo-Saxon rule and the beginning of Norman influence on language, law, and architecture."
    },
    {
        "topic": "History",
        "title": "The Fall of Constantinople (1453)",
        "content": "Ottoman Sultan Mehmed II conquered the Byzantine capital, ending the Roman Empire. This event spurred the European Renaissance as Greek scholars fled west with ancient manuscripts."
    },
    {
        "topic": "History",
        "title": "The Moon Landing (1969)",
        "content": "Apollo 11's Neil Armstrong and Buzz Aldrin became the first humans on the Moon. 'One small step for man, one giant leap for mankind' – a triumph of science and Cold War competition."
    },
    {
        "topic": "Science",
        "title": "Photosynthesis",
        "content": "Plants convert sunlight, water, and CO₂ into glucose and oxygen. This process produces ~50% of Earth's atmospheric oxygen and is the foundation of almost all food chains."
    },
    {
        "topic": "Science",
        "title": "Theory of Relativity",
        "content": "Einstein showed that time and space are relative, not absolute. GPS satellites must correct for both special and general relativity – otherwise, they'd be off by ~10 km per day!"
    },
    {
        "topic": "Science",
        "title": "The Structure of DNA",
        "content": "Watson & Crick discovered the double helix in 1953. DNA stores genetic instructions using four bases: A, T, C, G. Human DNA contains about 3 billion base pairs."
    },
    {
        "topic": "Geography",
        "title": "The Amazon Rainforest",
        "content": "Spans 9 countries and covers ~5.5 million km². It produces 20% of the world's oxygen and is home to 10% of all known species. Deforestation remains its biggest threat."
    },
    {
        "topic": "Geography",
        "title": "The Mariana Trench",
        "content": "The deepest point on Earth – Challenger Deep – reaches ~11,000 meters below sea level. Pressure there is over 1,000 times standard atmospheric pressure."
    },
    {
        "topic": "Geography",
        "title": "The Sahara Desert",
        "content": "The world's largest hot desert (9.2 million km²). It expands southward by about 48 km every year. Despite the heat, temperatures can drop below freezing at night."
    },
    {
        "topic": "Economics",
        "title": "Supply and Demand",
        "content": "Prices adjust to balance quantity supplied and quantity demanded. If demand exceeds supply, prices rise – incentivising producers to make more. It's the invisible hand that drives markets."
    },
    {
        "topic": "Economics",
        "title": "Inflation",
        "content": "Inflation is the general rise in prices over time. Moderate inflation (2-3%) is healthy; hyperinflation destroys savings. Central banks use interest rates to control it."
    },
    {
        "topic": "Economics",
        "title": "Opportunity Cost",
        "content": "The value of the next best alternative you give up when making a choice. If you spend 1 hour on a lesson, you forego 1 hour of leisure. Every decision has a hidden cost."
    },
]

def get_daily_lesson():
    return random.choice(LESSONS)

# ---------- BOT COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    lesson = get_daily_lesson()
    welcome = (
        f"🎓 Welcome to TinyTutor, {user.first_name}!\n\n"
        f"Here's your first 5‑minute lesson:\n\n"
        f"📖 *{lesson['title']}*\n"
        f"📂 *Topic:* {lesson['topic']}\n\n"
        f"{lesson['content']}\n\n"
        f"⏰ I'll send you a fresh lesson every day at 9:00 AM UTC.\n"
        f"Send /stop anytime to unsubscribe."
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    remove_user(user.id)
    await update.message.reply_text(
        "✅ You have been unsubscribed from TinyTutor.\n"
        "Send /start to resubscribe anytime."
    )

# ---------- BACKGROUND JOB ----------
async def send_daily_lessons(app: Application):
    users = get_all_users()
    if not users:
        logger.info("No users to send lessons to.")
        return

    lesson = get_daily_lesson()
    text = (
        f"📚 *Daily TinyTutor Lesson*\n\n"
        f"📖 *{lesson['title']}*\n"
        f"📂 *Topic:* {lesson['topic']}\n\n"
        f"{lesson['content']}\n\n"
        f"🧠 See you tomorrow for another bite‑sized lesson!"
    )

    for user_id in users:
        try:
            await app.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
            await asyncio.sleep(0.1)  # gentle rate limit
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")

# ---------- GRACEFUL SHUTDOWN ----------
async def shutdown(app: Application, scheduler: AsyncIOScheduler):
    logger.info("Shutting down gracefully...")
    scheduler.shutdown(wait=False)          # stop accepting new jobs
    await app.shutdown()                    # clean up bot resources
    logger.info("Shutdown complete.")

# ---------- MAIN ----------
async def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))

    # Set up daily scheduler (9:00 AM UTC)
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        send_daily_lessons,
        "cron",
        hour=9,
        minute=0,
        args=[app]
    )
    scheduler.start()
    logger.info("✅ Scheduler started. Daily lessons at 9:00 AM UTC.")

    # Register signal handlers for clean exit
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown(app, scheduler))
        )

    # Start polling – this blocks until stopped
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
