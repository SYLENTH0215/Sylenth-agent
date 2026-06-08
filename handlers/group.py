import logging
import uuid
from aiogram import Router, types, F, Bot
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from database import save_group, get_history, save_message, increment_msg_count
from ai_engine import ask_ai, ask_gemini, is_toxic
from utils import get_image_url, web_search

router = Router()

@router.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def bot_added(event: types.ChatMemberUpdated):
    """Bot guruhga qo'shilgani haqida xabar"""
    if event.chat.type in ("group", "supergroup"):
        save_group(event.chat.id, event.chat.title or "")
        try:
            await event.bot.send_message(
                event.chat.id,
                "👋 Salom! Men <b>SYLENTH Agent</b>man.\n\n"
                "📋 Foydalanish:\n"
                "• Menga javob qilish\n"
                "• @bot_username savol yozing\n\n"
                "Hozir tayyor 🚀",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Bot added xatosi: {e}")

@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def handle_group(message: types.Message, bot: Bot):
    """Guruhda xabar boshqarish"""
    me           = await bot.get_me()
    bot_username = f"@{me.username}".lower()
    is_mention   = message.text and bot_username in message.text.lower()
    is_reply     = (message.reply_to_message and
                    message.reply_to_message.from_user and
                    message.reply_to_message.from_user.id == me.id)
    
    if not (is_mention or is_reply):
        return

    text = (message.text or "").replace(bot_username, "").strip()
    if not text:
        return await message.reply("Ha, tinglayman! 👂")
    
    if is_toxic(text):
        return await message.reply("⛔ Bunday mavzularda javob bera olmayman.")


    thinking = await message.reply("⏳ Javob tayyorlanmoqda...")
    try:
        history = get_history(message.chat.id, limit=6)
        # Ask AI uchun history ni proper format ga o'girish
        reply = await ask_ai(text, history=history)
        save_message(message.chat.id, message.from_user.id, "user", text)
        save_message(message.chat.id, message.from_user.id, "model", reply)
        increment_msg_count(message.from_user.id)
        await message.reply(reply, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Guruh xatosi: {e}")
        await message.reply("⚠️ Vaqtinchalik nosozlik.")
    finally:
        try:
            await thinking.delete()
        except:
            pass

@router.inline_query()
async def inline_handler(query: InlineQuery):
    """Inline rejimi - @bot_username orqali javob"""
    text = query.query.strip()
    if not text:
        return await query.answer([], cache_time=5)
    
    results = []
    try:
        # AI javob
        ai_reply = await ask_ai(text)
        results.append(InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"🧠 {text[:50]}",
            description=ai_reply[:100],
            input_message_content=InputTextMessageContent(
                message_text=f"❓ <b>{text}</b>\n\n{ai_reply}", 
                parse_mode="HTML"
            )
        ))
    except Exception as e:
        logging.error(f"AI inline xatosi: {e}")

    # Rasm yaratish
    try:
        image_url = get_image_url(text)
        results.append(InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"🎨 Rasm: {text[:40]}",
            description="Flux.1 bilan AI rasm",
            input_message_content=InputTextMessageContent(
                message_text=f"🎨 <b>{text}</b>\n{image_url}", 
                parse_mode="HTML"
            )
        ))
    except Exception as e:
        logging.error(f"Image inline xatosi: {e}")

    # Veb qidiruv
    try:
        search_result = web_search(text)
        if search_result:
            results.append(InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"🔍 Qidiruv: {text[:40]}",
                description=search_result[:100],
                input_message_content=InputTextMessageContent(
                    message_text=f"🔍 <b>{text}</b>\n\n{search_result}", 
                    parse_mode="HTML"
                )
            ))
    except Exception as e:
        logging.error(f"Search inline xatosi: {e}")

    await query.answer(results=results[:3], cache_time=10)
