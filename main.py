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

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('mijozlar.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders 
                      (id INTEGER PRIMARY KEY, info TEXT, date TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def save_reminder(info, days):
    remind_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
    conn = sqlite3.connect('mijozlar.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reminders (info, date, status) VALUES (?, ?, ?)", (info, remind_date, 'pending'))
    conn.commit()
    conn.close()
    return remind_date

async def check_jobs():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn = sqlite3.connect('mijozlar.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, info FROM reminders WHERE date <= ? AND status = 'pending'", (now,))
    for rid, info in cursor.fetchall():
        try:
            await bot.send_message(ADMIN_ID, f"🔔 **ESLATMA!**\n\n{info}")
            cursor.execute("UPDATE reminders SET status = 'done' WHERE id = ?", (rid,))
        except: pass
    conn.commit()
    conn.close()

# --- BOT FUNKSIYALARI ---
@dp.message(Command("start"))
async def start(m: types.Message):
    if m.from_user.id == ADMIN_ID:
        await m.answer("✅ Bot tayyor! Mijoz haqida yozing.")

@dp.message(F.text)
async def handle_text(m: types.Message):
    if m.from_user.id == ADMIN_ID:
        kb = InlineKeyboardBuilder()
        for d in [1, 3, 5, 10, 15, 30]:
            kb.button(text=f"{d} kun", callback_data=f"d_{d}_{m.text[:20]}")
        kb.adjust(3)
        await m.answer(f"⏳ Muddatni tanlang:\n\n`{m.text}`", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("d_"))
async def callback(c: types.CallbackQuery):
    _, days, info_part = c.data.split("_")
    full_info = c.message.text.split("\n\n")[1]
    date = save_reminder(full_info, int(days))
    await c.message.edit_text(f"✅ Saqlandi!\n⏰ Eslatma: {date}")

# --- RENDER PORTINI ALDASH (WEB SERVER) ---
async def handle(request):
    return web.Response(text="Bot is Live")

async def main():
    init_db()
    scheduler.add_job(check_jobs, "interval", minutes=1)
    scheduler.start()
    
    # Render talab qiladigan veb qismi
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
