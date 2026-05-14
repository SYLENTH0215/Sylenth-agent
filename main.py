import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# --- YANGILANGAN KONFIGURATSIYA (2026-yil, May) ---
BOT_TOKEN = "8701673908:AAGk2e6J8X79AvVE2VuajywwiuvnK_GhqC8"
DEEPSEEK_KEY = "sk-c5ecf085378146fea99fff7b49cc5b93"
ADMIN_ID = 20100215
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Modullarni import qilish (Fayllar mavjudligini tekshiring)
try:
    from database import init_db
    from keyboards import get_main_menu
    from states import UserMode
    from handlers import commands, messages, group
except ImportError as e:
    logging.error(f"❌ Fayl topilmadi: {e}")

# Bot obyektini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Routerlarni ulash
dp.include_router(commands.router)
dp.include_router(messages.router)
dp.include_router(group.router)

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
        await callback.answer(f"✅ {mode.capitalize()} rejimi faollashdi")
    else:
        await callback.answer("Noma'lum rejim")

async def main():
    # Ma'lumotlar bazasini ochish
    try:
        init_db()
    except Exception as e:
        logging.error(f"MB xatosi: {e}")

    logging.info(f"🚀 SYLENTH Agent yangi DeepSeek API bilan ishga tushdi!")
    
    # Botni ishga tushirish
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
    
