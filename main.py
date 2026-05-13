import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

from database import init_db
from keyboards import get_main_menu
from states import UserMode
from handlers import commands, messages, group

bot = Bot(token=os.getenv("BOT_TOKEN"))
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
    new_state, text = mode_map[mode]
    await state.set_state(new_state)
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer(f"✅ Rejim o'zgartirildi")

async def main():
    init_db()
    logging.info("🚀 SYLENTH Agent ishga tushdi!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
