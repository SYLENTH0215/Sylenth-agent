"""
Private message handler.
Handles all messages in private (direct) chat with the bot.
- Video URL auto-detection and download
- AI-driven text responses with function calling
- Music search results shown as inline buttons
- Callback query handler for music selection
- Document/file analysis support
"""

import logging
import os
from pathlib import Path

from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_or_create_user
from bot.ai_engine import get_ai_response
from bot.downloader import (
    is_video_url,
    download_video,
    download_music_by_url,
    cleanup_file,
    extract_url,
)
from bot.file_analyzer import analyze_file

logger = logging.getLogger(__name__)

router = Router(name="private")

# Only handle private messages
router.message.filter(F.chat.type == "private")

# Downloads directory for temporary files
DOWNLOADS_DIR = "downloads"


def _ensure_downloads_dir() -> None:
    """Create downloads directory if it doesn't exist."""
    Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)


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


def _format_duration(seconds: int) -> str:
    """Format seconds into MM:SS string."""
    if not seconds:
        return ""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def _build_music_keyboard(music_results: list) -> InlineKeyboardMarkup:
    """
    Build an InlineKeyboardMarkup with music search results as buttons.

    Args:
        music_results: List of dicts with title, artist, duration, video_id

    Returns:
        InlineKeyboardMarkup with one button per result
    """
    buttons = []
    for i, result in enumerate(music_results[:5], 1):
        title = result.get("title", "Noma'lum")
        artist = result.get("artist", "")
        duration = _format_duration(result.get("duration", 0))
        video_id = result.get("video_id", "")

        # Build button text (truncate if too long)
        btn_text = f"{i}. {title}"
        if artist:
            btn_text += f" - {artist}"
        if duration:
            btn_text += f" [{duration}]"

        # Telegram limits callback_data to 64 bytes
        if len(btn_text) > 60:
            btn_text = btn_text[:57] + "..."

        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"music:{video_id}",
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _handle_video_url(message: types.Message, url: str) -> None:
    """Handle a video URL - download and send."""
    status_msg = await message.answer("📹 Video yuklanmoqda... ⏳")

    try:
        await message.answer_chat_action(action="upload_video")
        file_path, title = await download_video(url)

        if file_path is None:
            await status_msg.edit_text(f"❌ {title}")
            return

        try:
            video_file = types.FSInputFile(file_path, filename=f"{title}.mp4")
            await message.answer_video(
                video=video_file,
                caption=f"📹 {title}",
            )
            await status_msg.delete()
        finally:
            cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Video handler error: {e}")
        await status_msg.edit_text(
            "❌ Video yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


@router.message(F.document)
async def handle_document(message: types.Message, bot: Bot) -> None:
    """
    Handle document uploads - download, analyze, and provide AI response.
    Supports PDF, DOCX, XLSX, code files, ZIP archives.
    """
    user = message.from_user
    if not user:
        return

    document = message.document
    if not document:
        return

    # Register user
    await get_or_create_user(
        tg_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    file_name = document.file_name or "unknown_file"
    file_size_mb = (document.file_size or 0) / (1024 * 1024)

    # Check file size (max 20MB for Telegram bot API download)
    if file_size_mb > 20:
        await message.answer(
            f"❌ Fayl hajmi juda katta ({file_size_mb:.1f} MB). "
            "Maksimal hajm: 20 MB."
        )
        return

    await message.answer_chat_action(action="typing")
    status_msg = await message.answer(f"📄 <b>{file_name}</b> tahlil qilinmoqda... ⏳")

    try:
        # Download the file
        _ensure_downloads_dir()
        file_path = os.path.join(DOWNLOADS_DIR, f"{user.id}_{file_name}")

        await bot.download(document, destination=file_path)

        # Analyze the file
        extracted_text = await analyze_file(file_path, file_name)

        # Clean up the downloaded file
        cleanup_file(file_path)

        # Build prompt for AI with extracted content
        user_caption = message.caption or ""
        ai_prompt = f"Foydalanuvchi '{file_name}' faylini yubordi.\n\n"
        if user_caption:
            ai_prompt += f"Foydalanuvchi izohi: {user_caption}\n\n"
        ai_prompt += f"Fayl mazmuni:\n{extracted_text}\n\nUshbu faylni tahlil qil va foydalanuvchiga yordam ber."

        # Get AI response about the file
        response = await get_ai_response(
            user_id=user.id,
            user_text=ai_prompt,
            user_name=user.first_name or user.full_name or "",
        )

        await status_msg.delete()

        # Send AI analysis
        content = response.get("content", "Faylni tahlil qilishda xatolik yuz berdi.")
        chunks = _split_long_message(content)
        for chunk in chunks:
            await message.answer(chunk)

    except Exception as e:
        logger.error(f"Document handler error: {e}")
        await status_msg.edit_text(
            "❌ Faylni tahlil qilishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


@router.message(F.text)
async def handle_private_message(message: types.Message) -> None:
    """
    Handle all private text messages.
    Priority:
    1. Video URL detection -> download video immediately
    2. Everything else -> AI decides (may search web, find music, or just chat)
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

    # 1. Check for video URL - download immediately (no AI needed)
    if is_video_url(text):
        url = extract_url(text)
        if url:
            await _handle_video_url(message, url)
            return

    # 2. AI-driven response (AI decides if it needs to search web, find music, etc.)
    await message.answer_chat_action(action="typing")

    try:
        response = await get_ai_response(
            user_id=user.id,
            user_text=text,
            user_name=user.first_name or user.full_name or "",
        )

        response_type = response.get("type", "text")
        content = response.get("content", "")
        music_results = response.get("music_results")

        if response_type == "music_results" and music_results:
            # Show music results as inline keyboard buttons
            keyboard = _build_music_keyboard(music_results)

            # Send AI text with keyboard
            if content:
                chunks = _split_long_message(content)
                # Send all chunks except the last without keyboard
                for chunk in chunks[:-1]:
                    await message.answer(chunk)
                # Send last chunk with keyboard
                await message.answer(chunks[-1], reply_markup=keyboard)
            else:
                await message.answer(
                    "🎵 Quyidagi natijalardan birini tanlang:",
                    reply_markup=keyboard,
                )
        else:
            # Regular text response
            if content:
                chunks = _split_long_message(content)
                for chunk in chunks:
                    await message.answer(chunk)
            else:
                await message.answer("Kechirasiz, javob olishda xatolik yuz berdi. 🔄")

    except Exception as e:
        logger.error(f"Private message handler error: {e}")
        await message.answer(
            "Kechirasiz, xatolik yuz berdi. Iltimos, qayta urinib ko'ring. 🔄"
        )


@router.callback_query(F.data.startswith("music:"))
async def handle_music_callback(callback: types.CallbackQuery) -> None:
    """
    Handle music selection callback - user tapped a music result button.
    Downloads the selected track and sends it as audio.
    """
    user = callback.from_user
    if not user or not callback.data:
        return

    # Extract video_id from callback data
    video_id = callback.data.replace("music:", "")
    if not video_id:
        await callback.answer("Xatolik: video ID topilmadi.", show_alert=True)
        return

    # Acknowledge the callback
    await callback.answer("🎵 Yuklanmoqda...")

    # Build YouTube URL from video_id
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Send status message
    message = callback.message
    if not message:
        return

    status_msg = await message.answer("🎵 Musiqa yuklanmoqda... ⏳")

    try:
        await message.answer_chat_action(action="upload_voice")
        file_path, metadata = await download_music_by_url(url)

        if file_path is None:
            error_text = metadata.get("error", "Musiqa yuklab olinmadi.")
            await status_msg.edit_text(f"❌ {error_text}")
            return

        title = metadata.get("title", "Musiqa")
        artist = metadata.get("artist", "")
        duration = metadata.get("duration", 0)

        try:
            audio_file = types.FSInputFile(file_path, filename=f"{title}.mp3")
            await message.answer_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                duration=int(duration) if duration else None,
                caption=f"🎵 {title}",
            )
            await status_msg.delete()
        finally:
            cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Music callback handler error: {e}")
        await status_msg.edit_text(
            "❌ Musiqa yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )
