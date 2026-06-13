"""
Shared utility functions for message handlers.
Used by both private.py and group.py to avoid code duplication.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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

        # Safety: truncate video_id to 11 chars (standard YouTube ID length)
        # to ensure callback_data stays within Telegram's 64-byte limit
        if len(video_id) > 11:
            video_id = video_id[:11]

        # Build button text (truncate if too long)
        btn_text = f"{i}. {title}"
        if artist:
            btn_text += f" - {artist}"
        if duration:
            btn_text += f" [{duration}]"

        # Telegram limits button text display
        if len(btn_text) > 60:
            btn_text = btn_text[:57] + "..."

        # Validate callback_data length (Telegram limit: 64 bytes)
        callback_data = f"music:{video_id}"
        if len(callback_data.encode("utf-8")) > 64:
            # Fallback: truncate video_id further to fit
            video_id = video_id[:8]
            callback_data = f"music:{video_id}"

        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=callback_data,
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
