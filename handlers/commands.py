"""
Command handlers for the Telegram bot.
Handles /start, /help, /clear commands.
All other interactions (search, music) are handled by AI automatically.
"""

import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandStart

from database import get_or_create_user, clear_history

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
        "🔍 Internetdan ma'lumot qidiraman (shunchaki so'rang)\n"
        "🎵 Musiqa topib beraman (qo'shiq nomini yozing)\n"
        "📹 Video yuklab beraman (link yuboring)\n"
        "📄 Fayllarni tahlil qilaman (PDF, DOCX, XLSX, kod, ZIP)\n"
        "💾 Suhbatimizni eslab qolaman\n\n"
        "Hech qanday buyruq kerak emas - shunchaki yozing, "
        "men hamma narsani avtomatik qilaman! 😊"
    )

    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Handle /help command - show all features."""
    help_text = (
        "📖 <b>Sylenth Bot - Yordam</b>\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam (shu sahifa)\n"
        "/clear - Suhbat tarixini tozalash\n\n"
        "<b>Imkoniyatlar (avtomatik - buyruq kerak emas):</b>\n"
        "🧠 <b>AI Suhbat</b> - Istalgan savolingizni yozing\n"
        "🔍 <b>Qidiruv</b> - \"Internetdan ... haqida ma'lumot ber\" deb yozing\n"
        "🎵 <b>Musiqa</b> - Qo'shiq nomini yoki \"... musiqasini top\" deb yozing\n"
        "📹 <b>Video</b> - YouTube, Instagram, TikTok, Facebook havolasini yuboring\n"
        "📄 <b>Fayl tahlili</b> - PDF, DOCX, XLSX, kod yoki ZIP fayl yuboring\n"
        "💾 <b>Xotira</b> - Men sizni eslab qolaman va moslashaman\n"
        "👥 <b>Guruh</b> - Guruhda @mention yoki reply orqali murojaat qiling\n\n"
        "<i>Menga oddiy matn yuboring - men avtomatik ravishda kerakli "
        "amalni bajaraman!</i>"
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
