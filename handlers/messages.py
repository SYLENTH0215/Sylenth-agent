import logging from aiogram import Router, types, F from aiogram.fsm.context import FSMContext from config import BAN_THRESHOLD from database import save_message, get_history, increment_msg_count, warn_user, ban_user from ai_engine import ask_ai, deep_think, is_toxic, analyze_image from utils import web_search, extract_pdf_text from states import UserMode

router = Router() TOXIC_REPLY = "⛔ Kechirasiz, men bunday mavzularda suhbatlasha olmayman.\nIltimos, foydali mavzuda murojaat qiling."

async def _ai_reply(message: types.Message, text: str, model_fn, **kwargs): chat_id = message.chat.id tg_id   = message.from_user.id history = get_history(chat_id)

if is_toxic(text):
    warns = warn_user(tg_id)
    if warns >= BAN_THRESHOLD:
        ban_user(tg_id, "Takroriy odobsiz so'rovlar")
        return await message.answer("🚫 Qoidabuzarlik sababli bloklandingiz.")
    return await message.answer(f"{TOXIC_REPLY}\n\n⚠️ Ogohlantirish: {warns}/{BAN_THRESHOLD}")

thinking = await message.answer("⏳ Javob tayyorlanmoqda...")
try:
    reply = await model_fn(text, **kwargs)
    save_message(chat_id, tg_id, "user", text)
    save_message(chat_id, tg_id, "model", reply)
    increment_msg_count(tg_id)
    for i in range(0, len(reply), 4000):
        await message.answer(reply[i:i+4000])
except Exception as e:
    logging.error(f"AI reply xatosi: {e}")
    await message.answer("⚠️ Vaqtinchalik nosozlik. Keyinroq urinib ko'ring.")
finally:
    await thinking.delete()

@router.message(UserMode.chat, F.text) async def handle_chat(message: types.Message): await _ai_reply(message, message.text, ask_ai)

@router.message(UserMode.search, F.text) async def handle_search(message: types.Message): status = await message.answer("🔍 Internetdan qidirilmoqda...") results = web_search(message.text) await status.delete() extra = f"📡 Internet natijalar:\n{results}\n\n" if results else "" await _ai_reply(message, message.text, ask_ai, extra_context=extra)

@router.message(UserMode.think, F.text) async def handle_think(message: types.Message): await _ai_reply(message, message.text, deep_think)

@router.message(UserMode.draw, F.text) async def handle_draw(message: types.Message): from handlers.media import send_image await send_image(message, message.text)

@router.message(UserMode.dl, F.text) async def handle_dl(message: types.Message): from handlers.media import smart_download await smart_download(message, message.text)

@router.message(F.photo) async def handle_photo(message: types.Message): status = await message.answer("👁 Rasm tahlil qilinmoqda...") try: photo   = message.photo[-1] file    = await message.bot.get_file(photo.file_id) io_file = await message.bot.download_file(file.file_path) img_b   = io_file.read() prompt  = message.caption or "Bu rasmda nima tasvirlangan? Batafsil tushuntir." if is_toxic(prompt): await status.delete() return await message.answer(TOXIC_REPLY) reply = await analyze_image(img_b, prompt) await message.answer(reply) except Exception as e: logging.error(f"Vision xatosi: {e}") await message.answer("⚠️ Rasmni tahlil qilib bo'lmadi.") finally: await status.delete()

@router.message(F.document) async def handle_document(message: types.Message): if not message.document.file_name.lower().endswith(".pdf"): return await message.answer("📎 Faqat <b>PDF</b> fayllarni o'qiy olaman.", parse_mode="HTML") status = await message.answer("📄 PDF o'qilmoqda...") try: file    = await message.bot.get_file(message.document.file_id) io_file = await message.bot.download_file(file.file_path) text    = extract_pdf_text(io_file.read()) if not text.strip(): await status.delete() return await message.answer("⚠️ PDF dan matn ajratib bo'lmadi.") question = message.caption or "Bu hujjatni qisqacha xulosala." await status.delete() await _ai_reply(message, question, ask_ai, extra_context=f"📄 PDF:\n{text}\n\n") except Exception as e: logging.error(f"PDF xatosi: {e}") await status.delete() await message.answer("⚠️ PDF ni o'qib bo'lmadi.")

@router.message(F.text) async def handle_default(message: types.Message, state: FSMContext): current = await state.get_state() if current is None: await state.set_state(UserMode.chat) await handle_chat(message)
