import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_ID, DOWNLOADS_DIR
from database import init_db
from handlers import commands, messages, media, ceo, group
from middlewares.anti_flood import AntiFloodMiddleware
from middlewares.access import AccessMiddleware


# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot va Dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Middlewares qo'shish
dp.message.middleware(AntiFloodMiddleware())
dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(AccessMiddleware())

# Routers qo'shish
dp.include_router(commands.router)
dp.include_router(ceo.router)
dp.include_router(group.router)
dp.include_router(media.router)
dp.include_router(messages.router)

async def on_startup():
    """Bot ishga tushishdan oldin bajariladi"""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    init_db()
    logger.info(f"🚀 SYLENTH Agent ishga tushdi! Admin ID: {ADMIN_ID}")

async def main():
    """Bot asosiy funksiyasi"""
    dp.startup.register(on_startup)
    
    # Webhook o'chirib chiqish (agar bor bo'lsa)
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("📡 Polling rejimida ishga tushdi...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot xatosi: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot to'xtatildi")
