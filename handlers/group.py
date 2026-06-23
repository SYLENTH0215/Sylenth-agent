"""
Group message handler.
Only responds when the bot is mentioned (@username) or replied to.
Auto-detects video URLs in groups without requiring @mention.
AI-driven responses with function calling for search and music.
Multi-stage status updates for downloads (Yuklanmoqda -> Botga yuklanmoqda -> Yuborildi).
"""

import logging
import re

from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_or_create_user
from bot.ai_engine import get_ai_response
from bot.safety import is_safe
from bot.downloader import (
    is_video_url,
    download_video,
    download_music_by_url,
    cleanup_file,
    extract_url,
)
from handlers.utils import _split_long_message, _format_duration, _build_music_keyboard

logger = logging.getLogger(__name__)

router = Router(name="group")

# Cached bot info to avoid calling bot.get_me() on every message
_cached_bot_username: str = ""
_cached_bot_id: int = 0

# Only handle group/supergroup messages
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def _is_bot_mentioned(message: types.Message, bot_username: str) -> bool:
    """Check if the bot is mentioned in the message (case-insensitive)."""
    if not message.text:
        return False

    target = f"@{bot_username}".lower()

    # Check for @username mention in text
    if target in message.text.lower():
        return True

    # Check entities for mention
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mention_text = message.text[entity.offset:entity.offset + entity.length]
                if mention_text.lower() == target:
                    return True

    return False


def _is_reply_to_bot(message: types.Message, bot_id: int) -> bool:
    """Check if the message is a reply to the bot's message."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id == bot_id
    return False


def _clean_mention(text: str, bot_username: str) -> str:
    """Remove bot mention from the text."""
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
    Auto-detects video URLs (no @mention needed).
    For AI chat (including music search), requires @mention or reply to bot.
    """
    global _cached_bot_username, _cached_bot_id

    user = message.from_user
    text = message.text

    if not user or not text:
        return

    # Cache bot info on first call
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

    # For AI chat, require @mention or reply to bot
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

        response_type = response.get("type", "text")
        content = response.get("content", "")
        music_results = response.get("music_results")

        if response_type == "music_results" and music_results:
            # Show music results as inline keyboard buttons
            keyboard = _build_music_keyboard(music_results)

            if content:
                chunks = _split_long_message(content)
                for chunk in chunks[:-1]:
                    await message.reply(chunk)
                await message.reply(chunks[-1], reply_markup=keyboard)
            else:
                await message.reply(
                    "🎵 Quyidagi natijalardan birini tanlang:",
                    reply_markup=keyboard,
                )
        else:
            # Regular text response
            if content:
                chunks = _split_long_message(content)
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await message.reply(chunk)
                    else:
                        await message.answer(chunk)
            else:
                await message.reply(
                    "Kechirasiz, javob olishda xatolik yuz berdi. 🔄"
                )

    except Exception as e:
        logger.error(f"Group message handler error: {e}")
        await message.reply(
            "Kechirasiz, xatolik yuz berdi. Iltimos, qayta urinib ko'ring. 🔄"
        )


async def _handle_group_video(message: types.Message, url: str) -> None:
    """
    Handle a video URL in a group - download and send.
    Multi-stage status: Yuklanmoqda -> Botga yuklanmoqda -> Yuborildi
    """
    status_msg = await message.reply("📹 Video yuklanmoqda... ⏳")

    # Create status callback for multi-stage updates
    async def update_status(text: str) -> None:
        try:
            await status_msg.edit_text(text)
        except Exception:
            pass

    try:
        await message.answer_chat_action(action="upload_video")

        # Download with status callback
        file_path, title = await download_video(url, status_callback=update_status)

        if file_path is None:
            await status_msg.edit_text(f"❌ {title}")
            return

        try:
            # Stage: Sending to Telegram
            try:
                await status_msg.edit_text("📤 Botga yuklanmoqda... ⏳")
            except Exception:
                pass

            await message.answer_chat_action(action="upload_video")
            video_file = types.FSInputFile(file_path, filename=f"{title}.mp4")
            await message.answer_video(
                video=video_file,
                caption=f"📹 {title}",
            )

            # Stage: Done
            try:
                await status_msg.edit_text("✅ Video yuborildi!")
            except Exception:
                pass
            try:
                await status_msg.delete()
            except Exception:
                pass

        finally:
            # Always cleanup the downloaded file
            cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Group video handler error: {e}")
        try:
            await status_msg.edit_text(
                "❌ Video yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("music:"))
async def handle_group_music_callback(callback: types.CallbackQuery) -> None:
    """
    Handle music selection callback in groups.
    Downloads the selected track and sends it as audio.
    Multi-stage status: Yuklanmoqda -> Botga yuklanmoqda -> Yuborildi
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

    message = callback.message
    if not message:
        return

    status_msg = await message.answer("🎵 Musiqa yuklanmoqda... ⏳")

    # Create status callback for multi-stage updates
    async def update_status(text: str) -> None:
        try:
            await status_msg.edit_text(text)
        except Exception:
            pass

    try:
        await message.answer_chat_action(action="upload_voice")

        # Download with status callback
        file_path, metadata = await download_music_by_url(
            url, status_callback=update_status
        )

        if file_path is None:
            error_text = metadata.get("error", "Musiqa yuklab olinmadi.")
            await status_msg.edit_text(f"❌ {error_text}")
            return

        title = metadata.get("title", "Musiqa")
        artist = metadata.get("artist", "")
        duration = metadata.get("duration", 0)

        try:
            # Stage: Sending to Telegram
            try:
                await status_msg.edit_text("📤 Botga yuklanmoqda... ⏳")
            except Exception:
                pass

            audio_file = types.FSInputFile(file_path, filename=f"{title}.mp3")
            await message.answer_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                duration=int(duration) if duration else None,
                caption=f"🎵 {title}",
            )

            # Stage: Done
            try:
                await status_msg.delete()
            except Exception:
                pass

        finally:
            # Always cleanup the downloaded file
            cleanup_file(file_path)

    except Exception as e:
        logger.error(f"Group music callback handler error: {e}")
        try:
            await status_msg.edit_text(
                "❌ Musiqa yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
            )
        except Exception:
            pass
