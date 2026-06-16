"""
Sylenth Agent Bot - Main entry point.
Configures and starts the Telegram bot with all handlers and middlewares.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from bot.downloader import cleanup_stale_downloads
from handlers import commands, group, private
from middlewares.throttle import ThrottleMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Actions to perform on bot startup."""
    # Initialize database
    await init_db()
    logger.info("Database initialized successfully.")

    # Create downloads directory
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Downloads directory ready.")

    # Remove stale files left over from previous runs
    cleanup_stale_downloads()
    logger.info("Stale downloads cleaned up.")

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username} ({bot_info.full_name})")


async def on_shutdown(bot: Bot) -> None:
    """Actions to perform on bot shutdown."""
    logger.info("Bot is shutting down... Goodbye!")


async def main() -> None:
    """Main function - configure and start the bot."""
    # Create bot instance
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Create dispatcher with memory storage
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware on both messages and callback queries
    throttle = ThrottleMiddleware()
    dp.message.middleware(throttle)
    dp.callback_query.middleware(throttle)

    # Include routers (order matters!)
    # Commands first, then group, then private (catch-all)
    dp.include_router(commands.router)
    dp.include_router(group.router)
    dp.include_router(private.router)

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    logger.info("Starting bot polling...")
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        # Detect the common "invalid/unauthorized token" failure and give an
        # actionable message instead of a cryptic crash. We inspect the error
        # type/text only - never log the token value itself.
        err_text = str(e).lower()
        if (
            "unauthorized" in err_text
            or "token is invalid" in err_text
            or "not enough rights" in err_text
            or "401" in err_text
        ):
            logger.critical(
                "Bot could not start: the Telegram API rejected the bot token. "
                "Set a valid BOT_TOKEN environment variable (get one from "
                "@BotFather) and restart. (error type: %s)",
                type(e).__name__,
            )
        else:
            logger.critical(f"Fatal error: {type(e).__name__}: {e}")
        sys.exit(1)
