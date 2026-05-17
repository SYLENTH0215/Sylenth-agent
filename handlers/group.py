import logging
import uuid
from aiogram import Router, types, F, Bot
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from database import save_group, get_history, save_message, increment_msg_count
from ai_engine import ask_gemini, is_toxic
from utils import get_image_url, web_search

router = Router()

@router.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def bot_added(event: types.ChatMemberUpdated):
    if event.chat.type in ("group", "supergroup"):
        save_group(event.chat.id, event.chat.title or "")
        try:
            await event.bot.send_message(
                event.chat.id,
                "👋 Salom! Men <b>SYLENTH Agent</b>man.\n"
                "Savol berish: <code>@bot_username savol</code> yoki menga reply qiling.",
                parse_mode="HTML"
            )
        except Exception:
            pass

@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def handle_group(message: types.Message, bot: Bot):
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

    thinking = await message.reply("⏳...")
    try:
        history = get_history(message.chat.id, limit=6)
        reply   = ask_gemini(text, history)
        save_message(message.chat.id, message.from_user.id, "user", text)
        save_message(message.chat.id, message.from_user.id, "model", reply)
        increment_msg_count(message.from_user.id)
        await message.reply(reply)
    except Exception as e:
        logging.error(f"Guruh xatosi: {e}")
        await message.reply("⚠️ Vaqtinchalik nosozlik.")
    finally:
        await thinking.delete()

@router.inline_query()
async def inline_handler(query: InlineQuery):
    text = query.query.strip()
    if not text:
        return await query.answer([], cache_time=5)
    results = []
    try:
        ai_reply = ask_gemini(text)
        results.append(InlineQueryResultArticle(
            id=str(uuid.uuid4()), title=f"🧠 {text[:50]}",
            description=ai_reply[:100],
            input_message_content=InputTextMessageContent(
                message_text=f"❓ <b>{text}</b>\n\n{ai_reply}", parse_mode="HTML"
            )
        ))
    except Exception:
        pass
    results.append(InlineQueryResultArticle(
        id=str(uuid.uuid4()), title=f"🎨 Rasm: {text[:40]}",
        description="Flux.1 bilan rasm",
        input_message_content=InputTextMessageContent(
            message_text=f"🎨 <b>{text}</b>\n{get_image_url(text)}", parse_mode="HTML"
        )
    ))
    await query.answer(results=results[:3], cache_time=10)
