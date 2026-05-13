from aiogram import Router, types, F
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
from database import save_group, save_message, get_history
from handlers.messages import ask_deepseek

router = Router()

# --- Bot guruhga qo'shilganda ---
@router.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def bot_added_to_group(event: types.ChatMemberUpdated):
    save_group(event.chat.id, event.chat.title or "")
    await event.bot.send_message(
        event.chat.id,
        "👋 Salom! Men <b>SYLENTH Agent</b>man.\n"
        "Menga savol berish uchun: @men_username savol\n"
        "Yoki /start yozing.",
        parse_mode="HTML"
    )

# --- Guruhda mention yoki reply ---
@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(message: types.Message):
    bot_info = await message.bot.get_me()
    bot_username = f"@{bot_info.username}"

    # Faqat mention yoki reply ga javob ber
    is_mention = message.text and bot_username.lower() in message.text.lower()
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if not (is_mention or is_reply):
        return

    text = message.text or ""
    text = text.replace(bot_username, "").strip()
    if not text:
        return await message.answer("Ha, tinglayman! 👂")

    await ask_deepseek(message, text)
