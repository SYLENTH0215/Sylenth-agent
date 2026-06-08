import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import REQUIRED_CHANNEL, ADMIN_ID
from database import get_or_create_user, get_user, clear_history, ban_user, unban_user
from keyboards import main_menu, subscribe_btn
from states import UserMode, CEOState

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or ""
    )
    await state.set_state(UserMode.chat)
    await message.answer(
        f"👋 Assalomu alaykum, <b>{message.from_user.first_name}</b>!\n\n"
        f"🤖 Men <b>SYLENTH Agent</b> — SYLENTH jamoasi tomonidan yaratilgan AI yordamchiman.\n\n"
        f"🆔 Sizning SYLENTH ID: <code>{user['sylenth_id']}</code>\n\n"
        f"Quyidagi rejimlardan birini tanlang:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 <b>SYLENTH Agent — Buyruqlar:</b>\n\n"
        "/start — Botni qayta ishga tushirish\n"
        "/clear — Suhbat tarixini tozalash\n"
        "/id — SYLENTH ID ingiz\n"
        "/draw tavsif — Rasm yaratish\n"
        "/music qo'shiq nomi — MP3 yuklash\n\n"
        "📸 Rasm yuboring — AI tahlil qiladi\n"
        "📄 PDF yuboring — AI o'qib javob beradi",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    clear_history(message.chat.id)
    await message.answer("🗑 Suhbat tarixi tozalandi!")

@router.message(Command("id"))
async def cmd_id(message: types.Message):
    user = get_user(message.from_user.id)
    if user:
        await message.answer(
            f"🆔 <b>Ma'lumotlaringiz:</b>\n\n"
            f"SYLENTH ID: <code>{user['sylenth_id']}</code>\n"
            f"Telegram ID: <code>{user['tg_id']}</code>\n"
            f"Jami xabarlar: <b>{user['msg_count']}</b>\n"
            f"Qo'shilgan: <b>{user['joined_at'][:10]}</b>",
            parse_mode="HTML"
        )

@router.message(Command("draw"))
async def cmd_draw(message: types.Message):
    prompt = message.text.replace("/draw", "").strip()
    if not prompt:
        return await message.answer("🎨 Misol: <code>/draw kiberpank shahar</code>", parse_mode="HTML")
    from handlers.media import send_image
    await send_image(message, prompt)

@router.message(Command("music"))
async def cmd_music(message: types.Message):
    query = message.text.replace("/music", "").strip()
    if not query:
        return await message.answer("🎵 Misol: <code>/music Shaxriyor Qodirov</code>", parse_mode="HTML")
    from handlers.media import download_and_send_music
    await download_and_send_music(message, query)

@router.message(Command("ban"))
async def cmd_ban(message: types.Message):
    # ADMIN_ID ni xavfsiz int turiga o'giramiz
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Foydalanish: /ban <tg_id> [sabab]")
    try:
        ban_user(int(parts[1]), " ".join(parts[2:]) if len(parts) > 2 else "Admin buyrug'i")
        await message.answer(f"🚫 {parts[1]} banlandi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")

@router.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Foydalanish: /unban <tg_id>")
    try:
        unban_user(int(parts[1]))
        await message.answer(f"✅ {parts[1]} unbanlandi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")

@router.message(Command("ceo"))
async def cmd_ceo(message: types.Message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    from keyboards import ceo_panel
    await message.answer("🛡 <b>CEO Boshqaruv Paneli</b>", reply_markup=ceo_panel(), parse_mode="HTML")

@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    if not REQUIRED_CHANNEL:
        return await callback.answer("✅ Ruxsat berildi!")
    try:
        member = await callback.bot.get_chat_member(REQUIRED_CHANNEL, callback.from_user.id)
        if member.status not in ("left", "kicked", "banned"):
            await callback.message.edit_text("✅ Obuna tasdiqlandi!", reply_markup=main_menu())
        else:
            await callback.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
    except Exception:
        await callback.answer("✅ Davom eting!")
