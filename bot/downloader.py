"""
Media download module using yt-dlp.
Supports video download from multiple platforms and music search/download.
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

import yt_dlp

logger = logging.getLogger(__name__)

# Configuration
DOWNLOADS_DIR = "downloads"
MAX_FILE_SIZE_MB = 50

# Supported video platforms
VIDEO_PLATFORMS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts",
    r"(?:https?://)?youtu\.be/",
    r"(?:https?://)?(?:www\.)?instagram\.com/(?:reel|p|tv)/",
    r"(?:https?://)?(?:www\.)?tiktok\.com/",
    r"(?:https?://)?(?:vm\.)?tiktok\.com/",
    r"(?:https?://)?(?:www\.)?facebook\.com/.*/videos/",
    r"(?:https?://)?(?:www\.)?facebook\.com/watch",
    r"(?:https?://)?fb\.watch/",
    r"(?:https?://)?(?:www\.)?facebook\.com/reel/",
]

_VIDEO_PATTERNS = [re.compile(p, re.IGNORECASE) for p in VIDEO_PLATFORMS]

# Music request keywords
MUSIC_KEYWORDS = [
    "musiqa", "qo'shiq", "qoshiq", "music", "song", "mp3",
    "kuylash", "kuy", "topib ber", "qo'shig'ini", "qoshigini",
    "ashula", "pesnya", "muzika", "mahnisi", "aytib ber",
]


def _ensure_downloads_dir() -> None:
    """Create downloads directory if it doesn't exist."""
    Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)


def is_video_url(text: str) -> bool:
    """
    Check if the text contains a supported video platform URL.

    Args:
        text: Message text to check

    Returns:
        True if a supported video URL is found
    """
    if not text:
        return False
    for pattern in _VIDEO_PATTERNS:
        if pattern.search(text):
            return True
    return False


def is_music_request(text: str) -> bool:
    """
    Check if the text looks like a music search request.

    Args:
        text: Message text to check

    Returns:
        True if the text contains music-related keywords
    """
    if not text:
        return False
    text_lower = text.lower()
    for keyword in MUSIC_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


def _extract_url(text: str) -> Optional[str]:
    """Extract the first URL from text."""
    url_pattern = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE,
    )
    match = url_pattern.search(text)
    return match.group(0) if match else None


async def download_video(url: str) -> Tuple[Optional[str], str]:
    """
    Download a video from a supported platform.

    Args:
        url: Video URL to download

    Returns:
        Tuple of (file_path, title) on success, or (None, error_message) on failure
    """
    _ensure_downloads_dir()

    ydl_opts = {
        "format": "best[ext=mp4][filesize<50M]/best[ext=mp4]/bestvideo+bestaudio/best",
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
        "merge_output_format": "mp4",
    }

    try:
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, "Video ma'lumotlarini olishda xatolik."

                title = info.get("title", "Video")
                filename = ydl.prepare_filename(info)

                # Handle merged files
                if not os.path.exists(filename):
                    # Try with mp4 extension
                    base = os.path.splitext(filename)[0]
                    filename = base + ".mp4"

                if not os.path.exists(filename):
                    return None, "Video yuklab olinmadi."

                # Check file size
                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.remove(filename)
                    return None, (
                        f"Video hajmi juda katta ({file_size_mb:.1f} MB). "
                        f"Maksimal hajm: {MAX_FILE_SIZE_MB} MB."
                    )

                return filename, title

        result = await loop.run_in_executor(None, _download)
        return result

    except Exception as e:
        logger.error(f"Video download error for {url}: {e}")
        error_msg = str(e)
        if "Unsupported URL" in error_msg:
            return None, "Bu havola qo'llab-quvvatlanmaydi."
        elif "Private video" in error_msg or "Sign in" in error_msg:
            return None, "Bu video yopiq (private) - yuklab bo'lmaydi."
        elif "unavailable" in error_msg.lower():
            return None, "Video mavjud emas yoki o'chirilgan."
        else:
            return None, "Video yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."


async def download_music(query: str) -> Tuple[Optional[str], dict]:
    """
    Search YouTube for music and download as MP3.

    Args:
        query: Music search query (song name, artist, etc.)

    Returns:
        Tuple of (file_path, metadata_dict) on success,
        or (None, error_dict) on failure
    """
    _ensure_downloads_dir()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
        "default_search": "ytsearch1",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)

                if info is None:
                    return None, {"error": "Musiqa topilmadi."}

                # ytsearch returns entries list
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]

                if info is None:
                    return None, {"error": "Musiqa topilmadi."}

                title = info.get("title", "Unknown")
                artist = info.get("uploader", info.get("artist", "Unknown"))
                duration = info.get("duration", 0)

                # Build expected filename
                video_id = info.get("id", "unknown")
                filename = os.path.join(DOWNLOADS_DIR, f"{video_id}.mp3")

                if not os.path.exists(filename):
                    # Try other possible filenames
                    base = os.path.join(DOWNLOADS_DIR, video_id)
                    for ext in [".mp3", ".m4a", ".webm", ".opus"]:
                        if os.path.exists(base + ext):
                            filename = base + ext
                            break

                if not os.path.exists(filename):
                    return None, {"error": "Musiqa yuklab olinmadi."}

                # Check file size
                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.remove(filename)
                    return None, {"error": f"Fayl hajmi juda katta ({file_size_mb:.1f} MB)."}

                metadata = {
                    "title": title,
                    "artist": artist,
                    "duration": duration,
                }

                return filename, metadata

        result = await loop.run_in_executor(None, _download)
        return result

    except Exception as e:
        logger.error(f"Music download error for query '{query}': {e}")
        return None, {"error": "Musiqa yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."}


def cleanup_file(path: str) -> None:
    """
    Remove a file after it has been sent.

    Args:
        path: Path to the file to remove
    """
    try:
        if path and os.path.exists(path):
            os.remove(path)
            logger.debug(f"Cleaned up file: {path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup file {path}: {e}")
