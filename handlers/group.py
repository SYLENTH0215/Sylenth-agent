"""
Group message handler.
Only responds when the bot is mentioned (@username) or replied to.
"""

import logging

from aiogram import Router, types, F, Bot

from database import get_or_create_user
from bot.ai_engine import get_ai_response
from bot.safety import is_safe

logger = logging.getLogger(__name__)

router = Router(name="group")

# Only handle group/supergroup messages
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def _split_long_message(text: str, max_length: int = 4096) -> list:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind(" ", 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return chunks


def _is_bot_mentioned(message: types.Message, bot_username: str) -> bool:
    """Check if the bot is mentioned in the message."""
    if not message.text:
        return False

    # Check for @username mention in text
    if f"@{bot_username}" in message.text.lower():
        return True

    # Check entities for mention
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mention_text = message.text[entity.offset:entity.offset + entity.length]
                if mention_text.lower() == f"@{bot_username}":
                    return True

    return False


def _is_reply_to_bot(message: types.Message, bot_id: int) -> bool:
    """Check if the message is a reply to the bot's message."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id == bot_id
    return False


def _clean_mention(text: str, bot_username: str) -> str:
    """Remove bot mention from the text."""
    import re
    cleaned = re.sub(
        rf"@{re.escape(bot_username)}\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


@router.message(F.text)
async def handle_group_message(message: types.Message, bot: Bot) -> None:
    """
    Handle group messages.
    Only responds when bot is mentioned or message is a reply to bot.
    """
    user = message.from_user
    text = message.text

    if not user or not text:
        return

    # Get bot info
    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""
    bot_id = bot_info.id

    # Check if we should respond
    mentioned = _is_bot_mentioned(message, bot_username)
    replied_to_bot = _is_reply_to_bot(message, bot_id)

    if not mentioned and not replied_to_bot:
        return

    # Register/update user
    await get_or_create_user(
        tg_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    # Clean the text (remove bot mention)
    clean_text = _clean_mention(text, bot_username) if mentioned else text

    if not clean_text.strip():
        await message.reply(
            "Assalomu alaykum! Menga savol bering - javob berishga tayyorman! 😊"
        )
        return

    # Apply safety filter
    if not is_safe(clean_text):
        await message.reply(
            "Kechirasiz, men bu mavzuda yordam bera olmayman. "
            "Iltimos, boshqa savol bering! 😊"
        )
        return

    # Show typing
    await message.answer_chat_action(action="typing")

    try:
        response = await get_ai_response(
            user_id=user.id,
            user_text=clean_text,
            user_name=user.first_name or user.full_name or "",
        )

        # Split and send response
        chunks = _split_long_message(response)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.answer(chunk)

    except Exception as e:
        logger.error(f"Group message handler error: {e}")
        await message.reply(
            "Kechirasiz, xatolik yuz berdi. Iltimos, qayta urinib ko'ring. 🔄"
        )
