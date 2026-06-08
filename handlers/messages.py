import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from config import BAN_THRESHOLD
from database import save_message, get_history, increment_msg_count, warn_user, ban_user
from ai_engine import ask_ai, deep_think, is_toxic, analyze_image
from utils import web_search, extract_pdf_text
from states import UserMode

router = Router()
TOXIC_REPLY = "⛔ Kechirasiz, men bunday mavzularda suhbatlasha olmayman.\nIltimos, foydali mavzuda murojaat qiling."

async def _ai_reply(message: types.Message, text: str, model_fn, **kwargs):
    """AI dan javob olish va foydalanuvchiga yuborish"""
    chat_id = message.chat.id
    tg_id   = message.from_user.id
    history = get_history(chat_id)

    if is_toxic(text):
        warns = warn_user(tg_id)
        if warns >= BAN_THRESHOLD:
            ban_user(tg_id, "Takroriy odobsiz so'rovlar")
            return await message.answer("🚫 Qoidabuzarlik sababli bloklandingiz.")
        return await message.answer(f"{TOXIC_REPLY}\n\n⚠️ Ogohlantirish: {warns}/{BAN_THRESHOLD}")

    thinking = await message.answer("⏳ Javob tayyorlanmoqda...")
    try:
        reply = await model_fn(text, history=history, **kwargs)
        save_message(chat_id, tg_id, "user", text)
        save_message(chat_id, tg_id, "model", reply)
        increment_msg_count(tg_id)
        
        # Uzun javobni bo'laklab yuborish
        for i in range(0, len(reply), 4000):
            await message.answer(reply[i:i+4000], parse_mode="HTML")
    except Exception as e:
        logging.error(f"AI reply xatosi: {e}")
        await message.answer("⚠️ Vaqtinchalik nosozlik. Keyinroq urinib ko'ring.")
    finally:
        try:
            await thinking.delete()
        except:
            pass

# Chat rejimi - oddiy suhbat
@router.message(UserMode.chat, F.text)
async def handle_chat(message: types.Message, state: FSMContext):
    """Ordinary chat mode"""
    await _ai_reply(message, message.text, ask_ai)

# Think rejimi - chuqur tahlil
@router.message(UserMode.think, F.text)
async def handle_think(message: types.Message, state: FSMContext):
    """Deep analysis mode"""
    await _ai_reply(message, message.text, deep_think)

# Search rejimi - veb qidiruv
@router.message(UserMode.search, F.text)
async def handle_search(message: types.Message, state: FSMContext):
    """Web search mode"""
    status = await message.answer("🔍 Qidirilmoqda...")
    try:
        result = web_search(message.text)
        if result:
            for i in range(0, len(result), 4000):
                await message.answer(result[i:i+4000], parse_mode="HTML")
        else:
            await message.answer("❌ Qidiruv natijalari topilmadi.")
    except Exception as e:
        logging.error(f"Search xatosi: {e}")
        await message.answer("⚠️ Qidiruv xatosi.")
    finally:
        try:
            await status.delete()
        except:
            pass

# Draw rejimi - rasm yaratish
@router.message(UserMode.draw, F.text)
async def handle_draw(message: types.Message, state: FSMContext):
    """Image generation mode"""
    from handlers.media import send_image
    await send_image(message, message.text)

# Download rejimi - media yuklash
@router.message(UserMode.dl, F.text)
async def handle_dl(message: types.Message, state: FSMContext):
    """Media download mode"""
    from handlers.media import smart_download
    await smart_download(message, message.text)

# Rasmni tahlil qilish
@router.message(F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    """Analyze photo"""
    try:
        file_id = message.photo[-1].file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        
        # Rasmni yuklab olish
        downloaded_file = await message.bot.download_file(file_path)
        image_bytes = downloaded_file.getvalue()
        
        # Rasmni tahlil qilish
        caption = message.caption or "Bu rasmni tahlil qil"
        thinking = await message.answer("📸 Rasm tahlil qilinmoqda...")
        
        try:
            result = await analyze_image(image_bytes, caption)
            for i in range(0, len(result), 4000):
                await message.answer(result[i:i+4000], parse_mode="HTML")
        except Exception as e:
            logging.error(f"Rasm tahlili xatosi: {e}")
            await message.answer("⚠️ Rasmni tahlil qilib bo'lmadi.")
        finally:
            try:
                await thinking.delete()
            except:
                pass
    except Exception as e:
        logging.error(f"Photo handler xatosi: {e}")
        await message.answer("⚠️ Rasmni yuklashda xato.")

# PDF faylni tahlil qilish
@router.message(F.document)
async def handle_document(message: types.Message, state: FSMContext):
    """Handle document (PDF)"""
    if not message.document.file_name or not message.document.file_name.lower().endswith('.pdf'):
        return await message.answer("📄 Faqat PDF fayllar qabul qilinadi.")
    
    try:
        file = await message.bot.get_file(message.document.file_id)
        downloaded_file = await message.bot.download_file(file.file_path)
        pdf_bytes = downloaded_file.getvalue()
        
        thinking = await message.answer("📖 PDF o'qilmoqda...")
        try:
            # PDF matnini chiqarish
            text = extract_pdf_text(pdf_bytes)
            if not text:
                return await message.answer("❌ PDF-dan matn chiqarilmadi.")
            
            # PDFni tahlil qilish
            prompt = message.caption or f"Bu PDF haqida qisqacha ma'lumot ber: {text[:500]}"
            result = await ask_ai(prompt)
            
            for i in range(0, len(result), 4000):
                await message.answer(result[i:i+4000], parse_mode="HTML")
        except Exception as e:
            logging.error(f"PDF tahlili xatosi: {e}")
            await message.answer("⚠️ PDF-ni tahlil qilib bo'lmadi.")
        finally:
            try:
                await thinking.delete()
            except:
                pass
    except Exception as e:
        logging.error(f"Document handler xatosi: {e}")
        await message.answer("⚠️ Hujjatni yuklashda xato.")

# Callback queries uchun rejim o'zgartirish
@router.callback_query(F.data == "mode_chat")
async def set_chat_mode(callback: types.CallbackQuery, state: FSMContext):
    """Set chat mode"""
    await state.set_state(UserMode.chat)
    await callback.message.edit_text("💬 <b>Suhbat rejimi</b> faol. Savolni yozing!", parse_mode="HTML")
    from keyboards import main_menu
    await callback.message.edit_reply_markup(reply_markup=main_menu())

@router.callback_query(F.data == "mode_think")
async def set_think_mode(callback: types.CallbackQuery, state: FSMContext):
    """Set deep think mode"""
    await state.set_state(UserMode.think)
    await callback.message.edit_text("🧠 <b>Chuqur tahlil rejimi</b> faol. Ko'proq ma'lumot uchun savolni yozing!", parse_mode="HTML")
    from keyboards import main_menu
    await callback.message.edit_reply_markup(reply_markup=main_menu())

@router.callback_query(F.data == "mode_search")
async def set_search_mode(callback: types.CallbackQuery, state: FSMContext):
    """Set search mode"""
    await state.set_state(UserMode.search)
    await callback.message.edit_text("🔍 <b>Qidiruv rejimi</b> faol. Qidirish atamasi yozing!", parse_mode="HTML")
    from keyboards import main_menu
    await callback.message.edit_reply_markup(reply_markup=main_menu())

@router.callback_query(F.data == "mode_draw")
async def set_draw_mode(callback: types.CallbackQuery, state: FSMContext):
    """Set image generation mode"""
    await state.set_state(UserMode.draw)
    await callback.message.edit_text("🎨 <b>Rasm yaratish rejimi</b> faol. Tavsif yozing!", parse_mode="HTML")
    from keyboards import main_menu
    await callback.message.edit_reply_markup(reply_markup=main_menu())

@router.callback_query(F.data == "mode_dl")
async def set_dl_mode(callback: types.CallbackQuery, state: FSMContext):
    """Set download mode"""
    await state.set_state(UserMode.dl)
    await callback.message.edit_text("📥 <b>Media yuklash rejimi</b> faol.\n\nLink yozing yoki musiqa nomini yuboring!", parse_mode="HTML")
    from keyboards import main_menu
    await callback.message.edit_reply_markup(reply_markup=main_menu())

@router.callback_query(F.data == "my_id")
async def show_my_id(callback: types.CallbackQuery):
    """Show user info"""
    from database import get_user
    user = get_user(callback.from_user.id)
    if user:
        await callback.message.edit_text(
            f"🆔 <b>Ma'lumotlaringiz:</b>\n\n"
            f"<b>SYLENTH ID:</b> <code>{user['sylenth_id']}</code>\n"
            f"<b>Telegram ID:</b> <code>{user['tg_id']}</code>\n"
            f"<b>Jami xabarlar:</b> <b>{user['msg_count']}</b>\n"
            f"<b>Qo'shilgan sana:</b> <b>{user['joined_at'][:10]}</b>",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    """Show help"""
    await callback.message.edit_text(
        "📖 <b>SYLENTH Agent — Buyruqlar va xususiyatlar:</b>\n\n"
        "<b>🎨 Rejimlar:</b>\n"
        "• 💬 Suhbat — Oddiy suhbat\n"
        "• 🧠 Chuqur tahlil — Batafsilroq javoblar\n"
        "• 🔍 Qidiruv — Internetda qidiruv\n"
        "• 🎨 Rasm yaratish — AI rasm generator\n"
        "• 📥 Media yuklash — YouTube, TikTok va boshqalardan\n\n"
        "<b>⌨️ Buyruqlar:</b>\n"
        "/start — Botni qayta ishga tushirish\n"
        "/help — Yordam\n"
        "/clear — Suhbat tarixini tozalash\n"
        "/id — Sizning ID\n"
        "/draw tavsif — Rasm yaratish\n"
        "/music musiqa nomi — MP3 yuklash\n\n"
        "<b>📁 Media:</b>\n"
        "• Rasmni yuboring — AI tahlil qiladi\n"
        "• PDF yuboring — AI o'qib javob beradi",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    """Back to main menu"""
    from keyboards import main_menu
    await state.set_state(UserMode.chat)
    await callback.message.edit_text(
        f"👋 Assalomu alaykum, <b>{callback.from_user.first_name}</b>!\n\n"
        "🤖 SYLENTH Agent sizga xizmat qilishga tayyor!",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    """Cancel current action"""
    from keyboards import main_menu
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.", reply_markup=main_menu())
