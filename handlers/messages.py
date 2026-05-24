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
        for i in range(0, len(reply), 4000):
            await message.answer(reply[i:i+4000])
    except Exception as e:
        logging.error(f"AI reply xatosi: {e}")
        await message.answer("⚠️ Vaqtinchalik nosozlik. Keyinroq urinib ko'ring.")
    finally:
        await thinking.delete()

# Matn, rasm, PDF, va default handlerlar shu yerda
# ... (qolgan handle_xxx funksiyalar oldingi koddan moslashtiriladi)
