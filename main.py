import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncioScheduler

# --- SOZLAMALAR ---
API_TOKEN = '7206103986:AAF-6eM0Z_g1jI_K64W_uOasw6Wv9qA2Y3Y'
ADMIN_ID = 5621437172 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncioScheduler()

# --- BAZANI SOZLASH ---
def init_db():
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders 
                      (id INTEGER PRIMARY KEY, client_info TEXT, remind_date TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(info, days):
    remind_at = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reminders (client_info, remind_date, status) VALUES (?, ?, ?)",
                   (info, remind_at, 'pending'))
    conn.commit()
    conn.close()
    return remind_at

def get_days_keyboard():
    builder = InlineKeyboardBuilder()
    muddatlar = [("1 kun", 1), ("3 kun", 3), ("5 kun", 5), ("10 kun", 10), ("15 kun", 15), ("30 kun", 30)]
    for text, day in muddatlar:
        builder.button(text=text, callback_data=f"set_{day}")
    builder.adjust(3)
    return builder.as_markup()

async def check_reminders():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, client_info FROM reminders WHERE remind_date <= ? AND status = 'pending'", (now,))
    jobs = cursor.fetchall()
    for job in jobs:
        rid, info = job
        try:
            await bot.send_message(ADMIN_ID, f"🔔 **ESLATMA!**\n\n{info}")
            cursor.execute("UPDATE reminders SET status = 'notified' WHERE id = ?", (rid,))
        except Exception: pass
    conn.commit()
    conn.close()

temp_data = {}

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("✅ Tayyor! Mijoz haqida yozing, muddatni tanlaymiz.")

@dp.message(F.text)
async def process_text(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        temp_data[ADMIN_ID] = message.text
        await message.answer("Ushbu mijoz uchun muddatni tanlang:", reply_markup=get_days_keyboard())

@dp.callback_query(F.data.startswith("set_"))
async def save_rem(callback: types.CallbackQuery):
    days = int(callback.data.split("_")[1])
    info = temp_data.get(ADMIN_ID, "Noma'lum")
    date = save_to_db(info, days)
    await callback.message.edit_text(f"✅ Saqlandi!\n\n📋 {info}\n⏰ Muddat: {days} kundan keyin ({date})")
    await callback.answer()

async def main():
    init_db()
    scheduler.add_job(check_reminders, "interval", minutes=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
