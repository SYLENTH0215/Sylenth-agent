"""
Command handlers for the Telegram bot.
Handles /start, /help, /clear, /search, /music commands.
"""

import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandStart

from database import get_or_create_user, clear_history
from bot.search import search_web
from bot.downloader import download_music, cleanup_file

logger = logging.getLogger(__name__)

router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    """Handle /start command - welcome message with bot personality."""
    user = message.from_user
    if not user:
        return

    # Register user in database
    await get_or_create_user(
        tg_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    welcome_text = (
        f"Assalomu alaykum, <b>{user.first_name}</b>! 👋\n\n"
        "Men <b>Sylenth</b> - sizning aqlli yordamchingizman! 🤖\n\n"
        "Mening imkoniyatlarim:\n"
        "🧠 Savollaringizga javob beraman\n"
        "🔍 Internetdan ma'lumot qidiraman\n"
        "🎵 Musiqa topib beraman\n"
        "📹 Video yuklab beraman\n"
        "💾 Suhbatimizni eslab qolaman\n\n"
        "Menga istalgan savolingizni yuboring yoki "
        "/help buyrug'ini bosib, barcha imkoniyatlarni ko'ring!"
    )

    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Handle /help command - show all features and commands."""
    help_text = (
        "📖 <b>Sylenth Bot - Yordam</b>\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam (shu sahifa)\n"
        "/clear - Suhbat tarixini tozalash\n"
        "/search <so'rov> - Internetdan qidirish\n"
        "/music <nomi> - Musiqa yuklab olish\n\n"
        "<b>Imkoniyatlar:</b>\n"
        "🧠 <b>AI Suhbat</b> - Istalgan savolingizni yozing\n"
        "🔍 <b>Qidiruv</b> - /search so'zidan keyin so'rovni yozing\n"
        "🎵 <b>Musiqa</b> - /music so'zidan keyin qo'shiq nomini yozing\n"
        "📹 <b>Video</b> - YouTube, Instagram, TikTok, Facebook havolasini yuboring\n"
        "💾 <b>Xotira</b> - Men sizni eslab qolaman va moslashaman\n"
        "👥 <b>Guruh</b> - Guruhda @mention yoki reply orqali murojaat qiling\n\n"
        "<i>Menga oddiy matn yuboring - men javob beraman!</i>"
    )

    await message.answer(help_text)


@router.message(Command("clear"))
async def cmd_clear(message: types.Message) -> None:
    """Handle /clear command - clear conversation history."""
    user = message.from_user
    if not user:
        return

    await clear_history(user.id)
    await message.answer(
        "🗑 Suhbat tarixingiz tozalandi!\n"
        "Eslatma: Men siz haqingizda eslab qolgan ma'lumotlar saqlanadi. "
        "Yangi suhbatni boshlashingiz mumkin! 😊"
    )


@router.message(Command("search"))
async def cmd_search(message: types.Message) -> None:
    """Handle /search command - web search using DuckDuckGo."""
    if not message.text:
        return

    # Extract query after /search
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "🔍 Qidiruv uchun so'rov kiriting.\n"
            "Masalan: /search Python dasturlash tili"
        )
        return

    query = parts[1].strip()

    # Show typing indicator
    await message.answer_chat_action(action="typing")

    # Perform search
    results = await search_web(query)
    await message.answer(results)


@router.message(Command("music"))
async def cmd_music(message: types.Message) -> None:
    """Handle /music command - find and download music."""
    if not message.text:
        return

    # Extract query after /music
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "🎵 Qo'shiq nomini kiriting.\n"
            "Masalan: /music Imron - Aldangan qiz"
        )
        return

    query = parts[1].strip()

    # Show upload audio action
    await message.answer_chat_action(action="upload_voice")
    status_msg = await message.answer(f"🎵 Qidirilmoqda: <b>{query}</b>...")

    try:
        file_path, metadata = await download_music(query)

        if file_path is None:
            error_text = metadata.get("error", "Musiqa topilmadi.")
            await status_msg.edit_text(f"❌ {error_text}")
            return

        # Send audio file
        title = metadata.get("title", query)
        artist = metadata.get("artist", "")
        duration = metadata.get("duration", 0)

        await message.answer_chat_action(action="upload_voice")

        audio_file = types.FSInputFile(file_path, filename=f"{title}.mp3")
        await message.answer_audio(
            audio=audio_file,
            title=title,
            performer=artist,
            duration=int(duration) if duration else None,
            caption=f"🎵 {title}",
        )

        # Clean up status message and file
        await status_msg.delete()
        cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Music command error: {e}")
        await status_msg.edit_text(
            "❌ Musiqa yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )
