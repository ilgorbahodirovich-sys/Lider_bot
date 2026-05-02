import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncioScheduler

# --- SIZNING MA'LUMOTLARINGIZ ---
API_TOKEN = '8745749730:AAF6Y8NeTLT77TI42fhXDoL3Nk-w9gSIpXA'
ADMIN_ID = 1190027941 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncioScheduler()

# --- BAZANI SOZLASH ---
def init_db():
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       client_info TEXT, 
                       remind_date TEXT, 
                       status TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(info, date):
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reminders (client_info, remind_date, status) VALUES (?, ?, ?)",
                   (info, date, 'pending'))
    conn.commit()
    conn.close()

# --- TUGMALAR ---
def get_reminder_keyboard(reminder_id):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Bog'landim", callback_data=f"done_{reminder_id}"))
    builder.row(types.InlineKeyboardButton(text="⏳ 1 kunga surish", callback_data=f"delay_{reminder_id}"))
    return builder.as_markup()

# --- ESLATMA TEKSHIRUVCHI (HAR DAQIQA ISHLAYDI) ---
async def check_reminders():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, client_info FROM reminders WHERE remind_date <= ? AND status = 'pending'", (now,))
    jobs = cursor.fetchall()
    
    for job in jobs:
        rid, info = job
        try:
            await bot.send_message(ADMIN_ID, f"🔔 **VAQTI KELDI!**\n\n{info}", reply_markup=get_reminder_keyboard(rid))
            cursor.execute("UPDATE reminders SET status = 'notified' WHERE id = ?", (rid,))
        except Exception as e:
            logging.error(f"Xabar yuborishda xatolik: {e}")
    
    conn.commit()
    conn.close()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("✅ Bot tayyor! Mijoz haqida yozing, 10 kundan keyin eslataman.")

@dp.message(F.text)
async def process_message(message: types.Message):
    if message.from_user.id != ADMIN_ID: 
        return

    client_text = message.text
    # 10 kunlik muddatni hisoblash
    remind_at = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d %H:%M')
    
    save_to_db(client_text, remind_at)
    await message.answer(f"💾 Saqlandi!\n📅 Eslatma vaqti: {remind_at}")

@dp.callback_query(F.data.startswith("done_"))
async def process_done(callback: types.CallbackQuery):
    rid = callback.data.split("_")[1]
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET status = 'completed' WHERE id = ?", (rid,))
    conn.commit()
    conn.close()
    await callback.message.edit_text(callback.message.text + "\n\n✅ **Yopildi.**")

@dp.callback_query(F.data.startswith("delay_"))
async def process_delay(callback: types.CallbackQuery):
    rid = callback.data.split("_")[1]
    new_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
    conn = sqlite3.connect('mijozlar_bazasi.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET remind_date = ?, status = 'pending' WHERE id = ?", (new_date, rid))
    conn.commit()
    conn.close()
    await callback.message.edit_text(callback.message.text + f"\n\n⏳ **1 kunga surildi ({new_date}).**")

async def main():
    init_db()
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
  
