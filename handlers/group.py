"""
Group message handler.
Only responds when the bot is mentioned (@username) or replied to.
Auto-detects video URLs and music requests in groups without requiring @mention.
"""

import logging

from aiogram import Router, types, F, Bot

from database import get_or_create_user
from bot.ai_engine import get_ai_response
from bot.safety import is_safe
from bot.downloader import (
    is_video_url,
    is_music_request,
    download_video,
    download_music,
    cleanup_file,
    extract_url,
)

logger = logging.getLogger(__name__)

router = Router(name="group")

# Cached bot info to avoid calling bot.get_me() on every message
_cached_bot_username: str = ""
_cached_bot_id: int = 0

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
    Auto-detects video URLs and music requests (no @mention needed for these).
    For regular AI chat, only responds when bot is mentioned or message is a reply to bot.
    """
    global _cached_bot_username, _cached_bot_id

    user = message.from_user
    text = message.text

    if not user or not text:
        return

    # Cache bot info on first call to avoid repeated API calls
    if not _cached_bot_username:
        bot_info = await bot.get_me()
        _cached_bot_username = bot_info.username or ""
        _cached_bot_id = bot_info.id

    bot_username = _cached_bot_username
    bot_id = _cached_bot_id

    # Register/update user
    await get_or_create_user(
        tg_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    # AUTO-DETECT: Video URLs (no @mention needed)
    if is_video_url(text):
        url = extract_url(text)
        if url:
            await _handle_group_video(message, url)
            return

    # AUTO-DETECT: Music requests (no @mention needed)
    if is_music_request(text):
        await _handle_group_music(message, text)
        return

    # For regular AI chat, require @mention or reply to bot
    mentioned = _is_bot_mentioned(message, bot_username)
    replied_to_bot = _is_reply_to_bot(message, bot_id)

    if not mentioned and not replied_to_bot:
        return

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


async def _handle_group_video(message: types.Message, url: str) -> None:
    """Handle a video URL in a group - download and send."""
    status_msg = await message.reply("\ud83d\udcf9 Video yuklanmoqda... \u23f3")

    try:
        await message.answer_chat_action(action="upload_video")
        file_path, title = await download_video(url)

        if file_path is None:
            await status_msg.edit_text(f"\u274c {title}")
            return

        try:
            video_file = types.FSInputFile(file_path, filename=f"{title}.mp4")
            await message.answer_video(
                video=video_file,
                caption=f"\ud83d\udcf9 {title}",
            )
            await status_msg.delete()
        finally:
            cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Group video handler error: {e}")
        await status_msg.edit_text(
            "\u274c Video yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


async def _handle_group_music(message: types.Message, text: str) -> None:
    """Handle a music request in a group - search and download."""
    # Remove music keywords from query for cleaner search
    clean_query = text
    music_words = [
        "musiqa", "qo'shiq", "qoshiq", "music", "song", "mp3",
        "kuylash", "kuy", "topib ber", "qo'shig'ini", "qoshigini",
        "ashula", "pesnya", "muzika", "mahnisi", "aytib ber",
        "topib", "ber", "yuklab", "qo'y",
    ]
    for word in music_words:
        clean_query = clean_query.lower().replace(word, "")
    clean_query = clean_query.strip()

    if not clean_query:
        clean_query = text

    status_msg = await message.reply(f"\ud83c\udfb5 Qidirilmoqda: <b>{clean_query}</b>... \u23f3")

    try:
        await message.answer_chat_action(action="upload_voice")
        file_path, metadata = await download_music(clean_query)

        if file_path is None:
            error_text = metadata.get("error", "Musiqa topilmadi.")
            await status_msg.edit_text(f"\u274c {error_text}")
            return

        title = metadata.get("title", clean_query)
        artist = metadata.get("artist", "")
        duration = metadata.get("duration", 0)

        try:
            audio_file = types.FSInputFile(file_path, filename=f"{title}.mp3")
            await message.answer_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                duration=int(duration) if duration else None,
                caption=f"\ud83c\udfb5 {title}",
            )
            await status_msg.delete()
        finally:
            cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Group music handler error: {e}")
        await status_msg.edit_text(
            "\u274c Musiqa yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )
