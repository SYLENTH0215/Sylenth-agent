import os
import asyncio
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import (
    clear_history, save_user, get_all_users, get_all_groups
)
from keyboards import get_main_menu
from states import UserMode

router = Router()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    save_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name
    )
    await state.set_state(UserMode.chat)
    await message.answer(
        "👋 <b>SYLENTH Agent</b> tizimiga xush kelibsiz!\n\n"
        "🧠 DeepSeek • 🎨 Flux AI • 🔍 Web Search • 👁 Vision • 📄 PDF\n\n"
        "Rejimni tanlang yoki to'g'ridan-to'g'ri yozing:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "<b>📖 SYLENTH Agent — Buyruqlar:</b>\n\n"
        "/start — Botni ishga tushirish\n"
        "/clear — Suhbat tarixini tozalash\n"
        "/draw &lt;tavsif&gt; — Rasm yaratish\n"
        "/search &lt;savol&gt; — Internetdan qidirish\n"
        "/think &lt;masala&gt; — Chuqur mantiqiy tahlil\n"
        "/broadcast — Barcha foydalanuvchilarga xabar (admin)\n"
        "/help — Yordam\n\n"
        "📎 Rasm yuborsang — tahlil qilaman\n"
        "📄 PDF yuborsang — o'qib javob beraman"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    clear_history(message.chat.id)
    await message.answer("🗑 Suhbat tarixi tozalandi.")

@router.message(Command("draw"))
async def cmd_draw(message: types.Message):
    prompt = message.text.replace("/draw", "").strip()
    if not prompt:
        return await message.answer("✏️ Misol: /draw kiberpank shahar")
    from utils import get_image_url
    status = await message.answer("🎨 Yaratilmoqda...")
    url = get_image_url(prompt)
    try:
        await message.answer_photo(url, caption=f"✨ <b>{prompt}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("⚠️ Rasm yaratib bo'lmadi, qayta urining.")
    await status.delete()

@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Ruxsat yo'q.")
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.answer("Xabar matnini yozing: /broadcast Salom!")

    users = get_all_users()
    groups = get_all_groups()
    targets = users + groups
    sent, failed = 0, 0

    for chat_id in targets:
        try:
            await bot.send_message(chat_id, f"📢 <b>SYLENTH:</b>\n{text}", parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.answer(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")
