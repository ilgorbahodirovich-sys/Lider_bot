import asyncio
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- SOZLAMALAR ---
API_TOKEN = '7206103986:AAF-6eM0Z_g1jI_K64W_uOasw6Wv9qA2Y3Y'
ADMIN_ID = 5621437172 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

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
        except Exception as e:
            logging.error(f"Eslatma yuborishda xato: {e}")
    conn.commit()
    conn.close()

temp_data = {}

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("✅ Bot ishga tushdi! Mijoz ma'lumotlarini yuboring (masalan: Ism, tel, ish turi).")

@dp.message(F.text)
async def process_text(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        temp_data[ADMIN_ID] = message.text
        await message.answer("Ushbu mijoz uchun muddatni tanlang:", reply_markup=get_days_keyboard())

@dp.callback_query(F.data.startswith("set_"))
async def save_rem(callback: types.CallbackQuery):
    days = int(callback.data.split("_")[1])
    info = temp_data.get(ADMIN_ID, "Noma'lum mijoz")
    date = save_to_db(info, days)
    await callback.message.edit_text(f"✅ Saqlandi!\n\n📋 {info}\n⏰ Eslatma vaqti: {date} ({days} kundan keyin)")
    await callback.answer()

# --- RENDER UCHUN VEB SERVER (PORTNI BAND QILISH) ---
async def handle(request):
    return web.Response(text="Lider Bot is running...")

async def main():
    init_db()
    # Eslatmalarni har minutda tekshirish
    scheduler.add_job(check_reminders, "interval", minutes=1)
    scheduler.start()
    
    # Render portini band qilish uchun veb-server
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"Veb-server {port} portida ishga tushdi")
    
    # Bot pollingni boshlash
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
