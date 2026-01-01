from apscheduler.schedulers.asyncio import AsyncIOScheduler
import sqlite3

scheduler = AsyncIOScheduler()


async def send_daily_tasks(bot, build_today_message):
    conn = sqlite3.connect("goals.db")
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT user_id FROM goals")
    users = cursor.fetchall()
    conn.close()

    for (user_id,) in users:
        text, keyboard = build_today_message(user_id)
        await bot.send_message(user_id, text, reply_markup=keyboard)


def start_scheduler(bot, close_day, build_today_message):
    # 📩 HAR KUNI 05:00
    scheduler.add_job(
        send_daily_tasks,
        trigger="cron",
        hour=5,
        minute=0,
        args=[bot, build_today_message]
    )

    # 🌙 HAR KUNI 23:59
    scheduler.add_job(
        close_day,
        trigger="cron",
        hour=23,
        minute=59
    )

    scheduler.start()
