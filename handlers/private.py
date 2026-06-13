"""
Private message handler.
Handles all text messages in private (direct) chat with the bot.
Detects video URLs, music requests, and regular AI chat.
"""

import logging

from aiogram import Router, types, F

from database import get_or_create_user
from bot.ai_engine import get_ai_response
from bot.downloader import (
    is_video_url,
    is_music_request,
    download_video,
    download_music,
    cleanup_file,
    _extract_url,
)

logger = logging.getLogger(__name__)

router = Router(name="private")

# Only handle private messages
router.message.filter(F.chat.type == "private")


def _split_long_message(text: str, max_length: int = 4096) -> list:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Try to split at a newline
        split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            # Try to split at a space
            split_pos = text.rfind(" ", 0, max_length)
        if split_pos == -1:
            # Force split at max_length
            split_pos = max_length

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return chunks


async def _handle_video_url(message: types.Message, url: str) -> None:
    """Handle a video URL - download and send."""
    status_msg = await message.answer("📹 Video yuklanmoqda... ⏳")

    try:
        await message.answer_chat_action(action="upload_video")
        file_path, title = await download_video(url)

        if file_path is None:
            await status_msg.edit_text(f"❌ {title}")
            return

        video_file = types.FSInputFile(file_path, filename=f"{title}.mp4")
        await message.answer_video(
            video=video_file,
            caption=f"📹 {title}",
        )

        await status_msg.delete()
        cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Video handler error: {e}")
        await status_msg.edit_text(
            "❌ Video yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


async def _handle_music_request(message: types.Message, query: str) -> None:
    """Handle a music search request - search and send."""
    # Remove music keywords from query for cleaner search
    clean_query = query
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
        # If nothing left after removing keywords, use original
        clean_query = query

    status_msg = await message.answer(f"🎵 Qidirilmoqda: <b>{clean_query}</b>... ⏳")

    try:
        await message.answer_chat_action(action="upload_voice")
        file_path, metadata = await download_music(clean_query)

        if file_path is None:
            error_text = metadata.get("error", "Musiqa topilmadi.")
            await status_msg.edit_text(f"❌ {error_text}")
            return

        title = metadata.get("title", clean_query)
        artist = metadata.get("artist", "")
        duration = metadata.get("duration", 0)

        audio_file = types.FSInputFile(file_path, filename=f"{title}.mp3")
        await message.answer_audio(
            audio=audio_file,
            title=title,
            performer=artist,
            duration=int(duration) if duration else None,
            caption=f"🎵 {title}",
        )

        await status_msg.delete()
        cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Music handler error: {e}")
        await status_msg.edit_text(
            "❌ Musiqa yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


@router.message(F.text)
async def handle_private_message(message: types.Message) -> None:
    """
    Handle all private text messages.
    Priority:
    1. Video URL detection -> download video
    2. Music request detection -> search and download music
    3. Default -> AI chat response
    """
    user = message.from_user
    text = message.text

    if not user or not text:
        return

    # Register/update user in database
    await get_or_create_user(
        tg_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    # 1. Check for video URL
    if is_video_url(text):
        url = _extract_url(text)
        if url:
            await _handle_video_url(message, url)
            return

    # 2. Check for music request
    if is_music_request(text):
        await _handle_music_request(message, text)
        return

    # 3. Default: AI chat response
    await message.answer_chat_action(action="typing")

    try:
        response = await get_ai_response(
            user_id=user.id,
            user_text=text,
            user_name=user.first_name or user.full_name or "",
        )

        # Handle long responses
        chunks = _split_long_message(response)
        for chunk in chunks:
            await message.answer(chunk)

    except Exception as e:
        logger.error(f"Private message handler error: {e}")
        await message.answer(
            "Kechirasiz, xatolik yuz berdi. Iltimos, qayta urinib ko'ring. 🔄"
        )
