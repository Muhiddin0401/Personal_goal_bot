import asyncio, logging, sys, os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from datetime import datetime
from datetime import date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scheduler import start_scheduler


# TOKEN = os.getenv("BOT_TOKEN")
TOKEN = "8507652805:AAE7YqHFqcIkR9YuxLb1FvyzAvIclJmBIFY"

dp = Dispatcher()
user_states = {}


def build_today_message(user_id: int):
    today = date.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect("goals.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            g.id,
            g.title,
            g.period_days,
            g.created_at,
            COALESCE(l.completed, 0)
        FROM goals g
        LEFT JOIN goal_logs l
          ON g.id = l.goal_id
         AND l.date = ?
         AND l.user_id = ?
        WHERE g.user_id = ?
    """, (today, user_id, user_id))

    rows = cursor.fetchall()
    conn.close()

    text = "📅 <b>Bugungi bajarishingiz kerak bo‘lgan ishlar:</b>\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for goal_id, title, period, created_at, completed in rows:
        created = datetime.fromisoformat(created_at).date()
        delta_days = (date.today() - created).days

        # 🔴 bugun chiqishi kerakmi?
        if delta_days % period != 0:
            continue

        if completed:
            text += f"✅ {title}\n"
        else:
            text += f"⬜ {title}\n"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=title,
                    callback_data=f"done:{goal_id}"
                )
            ])

    if not keyboard.inline_keyboard:
        keyboard = None

    return text, keyboard

def close_day():
    conn = sqlite3.connect("goals.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT user_id, last_message_id
        FROM goals
        WHERE last_message_id IS NOT NULL
    """)

    # eski logikang qoladi
    cursor.execute("""
        INSERT INTO goal_logs (user_id, goal_id, date, completed)
        SELECT g.user_id, g.id, DATE('now'), 0
        FROM goals g
        WHERE NOT EXISTS (
            SELECT 1 FROM goal_logs l
            WHERE l.goal_id = g.id AND l.date = DATE('now')
        )
    """)

    conn.commit()
    conn.close()

    print("✅ Kun yopildi va eski xabar o‘chirildi")




@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🎯 Maqsadlar botiga xush kelibsiz!\n\n"
        "/add_goal – yangi maqsad\n"
        "/stats – statistika\n"
        "/help – yordam oynasi\n\n"
    )

@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "🤖 <b>MAQSADLAR BOTI – YORDAM</b>\n\n"
        "Bu bot sizga kundalik, haftalik va oylik\n"
        "maqsadlaringizni nazorat qilishga yordam beradi.\n\n"

        "📌 <b>QANDAY ISHLAYDI?</b>\n"
        "1️⃣ Maqsad qo‘shasiz\n"
        "2️⃣ Bot har kuni soat 05:00 da eslatadi\n"
        "3️⃣ Bajarilgan maqsadni tugma orqali belgilaysiz\n"
        "4️⃣ Statistikani ko‘rib borasiz\n\n"

        "📘 <b>BUYRUQLAR:</b>\n"
        "/start – Botni ishga tushirish\n"
        "/add_goal – Yangi maqsad qo‘shish\n"
        "/stats – Oxirgi 7 kun statistikasi\n"
        "/help – Ushbu yordam oynasi\n\n"

        "📝 <b>MAQSAD MISOLLARI:</b>\n"
        "• Kuniga 10 bet kitob o‘qish (1)\n"
        "• Haftasiga 3 marta sport (7)\n"
        "• Oyiga 1 marta kitob tugatish (30)\n\n"

        "🎯 <i>Intizom – katta natijalarning boshlanishi.</i>"
    )


@dp.message(Command("add_goal"))
async def add_goal(message: Message):
    await message.answer("✍️ Maqsadingizni yozing:")
    user_states[message.from_user.id] = "title"


def get_db():
    return sqlite3.connect("goals.db")

@dp.message(Command("stats"))
async def stats_handler(message: Message):
    user_id = message.from_user.id
    today = date.today()

    db = get_db()
    cursor = db.cursor()

    response = "📊 <b>Oxirgi 7 kun statistikasi</b>\n\n"

    for i in range(7):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT g.title, l.completed
            FROM goal_logs l
            JOIN goals g ON g.id = l.goal_id
            WHERE l.user_id = ? AND l.date = ?
        """, (user_id, day_str))

        rows = cursor.fetchall()

        response += f"📅 <b>{day.strftime('%d %B')}</b>\n"

        if not rows:
            response += "➖ Maqsad belgilanmagan\n\n"
            continue

        done = [r[0] for r in rows if r[1] == 1]
        not_done = [r[0] for r in rows if r[1] == 0]

        if done:
            response += "✅ <b>Bajarilgan:</b>\n"
            for g in done:
                response += f"• {g}\n"

        if not_done:
            response += "❌ <b>Bajarilmagan:</b>\n"
            for g in not_done:
                response += f"• {g}\n"

        response += "\n"

    db.close()
    await message.answer(response)


@dp.message(F.text)
async def catch_text(message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == "title":
        user_states[user_id] = {
            "step": "period",
            "title": message.text
        }
        await message.answer("🔁 Necha kunda bir marta? (1 / 7 / 30)")

    elif isinstance(state, dict) and state.get("step") == "period":
        try:
            period = int(message.text)
        except ValueError:
            await message.answer("❗ Iltimos, raqam kiriting (1 / 7 / 30)")
            return

        conn = sqlite3.connect("goals.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO goals (user_id, title, period_days, created_at) VALUES (?, ?, ?, ?)",
            (user_id, state["title"], period, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        user_states.pop(user_id, None)
        await message.answer("✅ Maqsad saqlandi!")


from aiogram.exceptions import TelegramBadRequest

@dp.callback_query(F.data.startswith("done:"))
async def mark_done(call: CallbackQuery):
    goal_id = int(call.data.split(":")[1])
    user_id = call.from_user.id
    today = date.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect("goals.db")
    cursor = conn.cursor()

    # 🔒 Agar allaqachon bajarilgan bo‘lsa – hech narsa qilmaymiz
    cursor.execute("""
        SELECT completed FROM goal_logs
        WHERE user_id = ? AND goal_id = ? AND date = ?
    """, (user_id, goal_id, today))

    row = cursor.fetchone()
    if row and row[0] == 1:
        conn.close()
        await call.answer("Bu maqsad allaqachon bajarilgan ✅", show_alert=True)
        return

    # ✅ Bajarildi deb belgilaymiz
    cursor.execute("""
        INSERT OR REPLACE INTO goal_logs (user_id, goal_id, date, completed)
        VALUES (?, ?, ?, 1)
    """, (user_id, goal_id, today))

    conn.commit()
    conn.close()

    # 🔁 Xabarni qayta yasaymiz
    text, keyboard = build_today_message(user_id)

    try:
        if call.message.text != text:
            await call.message.edit_text(text)

        await call.message.edit_reply_markup(
            reply_markup=keyboard if keyboard else None
        )
    except TelegramBadRequest:
        # Telegram: "message is not modified" – xavfsiz ignore
        pass

    await call.answer("Bajarildi ✅")




async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    start_scheduler(bot, close_day, build_today_message)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
