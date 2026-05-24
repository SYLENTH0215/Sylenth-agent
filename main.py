import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_ID, DOWNLOADS_DIR
from handlers import commands, messages, media, ceo, group
from middlewares.anti_flood import AntiFloodMiddleware
from middlewares.access import AccessMiddleware

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
dp.message.middleware(AntiFloodMiddleware())
dp.message.middleware(AccessMiddleware())
dp.include_router(commands.router)
dp.include_router(ceo.router)
dp.include_router(group.router)
dp.include_router(media.router)
dp.include_router(messages.router)

async def on_startup():
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    logging.info("🚀 SYLENTH Agent ishga tushdi!")

async def main():
    dp.startup.register(on_startup)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
