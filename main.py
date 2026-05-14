import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# --- YANGILANGAN KONFIGURATSIYA ---
BOT_TOKEN = "8701673908:AAGk2e6J8X79AvVE2VuajywwiuvnK_GhqC8"
DEEPSEEK_KEY = "sk-cc0d6273dd284087b41bc15ab32dfcd1"
ADMIN_ID = 20100215
# ----------------------------------

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Modullarni import qilish
# DIQQAT: Bu fayllar main.py bilan bir xil papkada bo'lishi shart!
try:
    from database import init_db
    from keyboards import get_main_menu
    from states import UserMode
    from handlers import commands, messages, group
except ImportError as e:
    logging.error(f"❌ Fayllar yetishmayapti: {e}")
    logging.info("Maslahat: database.py, keyboards.py, states.py va handlers/ papkasini tekshiring.")

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Routerlarni ulash
try:
    dp.include_router(commands.router)
    dp.include_router(messages.router)
    dp.include_router(group.router)
except NameError:
    logging.warning("⚠️ Routerlar yuklanmadi, importlarni tekshiring.")

# Callback handler (rejim tanlash)
@dp.callback_query(F.data.startswith("mode_"))
async def on_mode_select(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]
    
    mode_map = {
        "draw":   (UserMode.draw,   "🎨 <b>Rasm rejimi</b> — tavsif yozing"),
        "search": (UserMode.search, "🔍 <b>Qidiruv rejimi</b> — savolingizni bering"),
        "think":  (UserMode.think,  "🧠 <b>Chuqur mantiq</b> — murakkab masalani yuboring"),
        "chat":   (UserMode.chat,   "💬 <b>Suhbat rejimi</b> — istalganini yozing"),
    }
    
    if mode in mode_map:
        new_state, text = mode_map[mode]
        await state.set_state(new_state)
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer(f"✅ Rejim o'zgartirildi")
    else:
        await callback.answer("❌ Xato: Rejim topilmadi")

async def main():
    # MB ishga tushirish
    try:
        init_db()
    except Exception as e:
        logging.error(f"❌ Baza xatosi: {e}")

    logging.info(f"🚀 SYLENTH Agent yangi token bilan ishga tushdi!")
    logging.info(f"Admin: {ADMIN_ID}")
    
    # Botni polling rejimida ishga tushirish
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
    
