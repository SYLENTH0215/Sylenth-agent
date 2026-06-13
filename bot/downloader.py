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
    Works with and without https:// prefix.

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

    # Also check without protocol prefix (e.g., youtube.com/watch?v=xxx)
    text_lower = text.lower()
    no_proto_indicators = [
        "youtube.com/watch", "youtube.com/shorts", "youtu.be/",
        "instagram.com/reel", "instagram.com/p/", "instagram.com/tv/",
        "tiktok.com/", "vm.tiktok.com/",
        "facebook.com/reel", "facebook.com/watch", "fb.watch/",
    ]
    for indicator in no_proto_indicators:
        if indicator in text_lower:
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


def extract_url(text: str) -> Optional[str]:
    """
    Extract the first URL from text.
    Handles URLs with or without http(s):// prefix.
    """
    # First try to find a full URL with protocol
    url_pattern = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE,
    )
    match = url_pattern.search(text)
    if match:
        return match.group(0)

    # Try to find URL without protocol (e.g. youtube.com/watch?v=xxx)
    no_proto_pattern = re.compile(
        r'(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|tiktok\.com|vm\.tiktok\.com|facebook\.com|fb\.watch)[^\s<>"{}|\\^`\[\]]*',
        re.IGNORECASE,
    )
    match = no_proto_pattern.search(text)
    if match:
        return "https://" + match.group(0)

    return None


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


async def search_music(query: str, max_results: int = 5) -> list:
    """
    Search YouTube for music and return a list of results WITHOUT downloading.
    Used to show inline keyboard buttons for user selection.

    Args:
        query: Music search query (song name, artist, etc.)
        max_results: Maximum number of results to return (default: 5)

    Returns:
        List of dicts: [{title, artist, duration, video_id, url}]
        Returns empty list on failure.
    """
    try:
        loop = asyncio.get_event_loop()

        def _search():
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "default_search": f"ytsearch{max_results}",
                "socket_timeout": 15,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

                if info is None:
                    return []

                entries = info.get("entries", [])
                if not entries:
                    return []

                results = []
                for entry in entries:
                    if entry is None:
                        continue
                    video_id = entry.get("id", "")
                    title = entry.get("title", "Noma'lum")
                    artist = entry.get("uploader", entry.get("channel", ""))
                    duration = entry.get("duration", 0)
                    url = entry.get("url", f"https://www.youtube.com/watch?v={video_id}")

                    results.append({
                        "title": title,
                        "artist": artist,
                        "duration": duration or 0,
                        "video_id": video_id,
                        "url": url,
                    })

                return results

        results = await loop.run_in_executor(None, _search)
        return results

    except Exception as e:
        logger.error(f"Music search error for query '{query}': {e}")
        return []


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


async def download_music_by_url(url: str) -> Tuple[Optional[str], dict]:
    """
    Download music from a specific YouTube URL as MP3.

    Args:
        url: YouTube video URL

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
                info = ydl.extract_info(url, download=True)

                if info is None:
                    return None, {"error": "Musiqa topilmadi."}

                title = info.get("title", "Unknown")
                artist = info.get("uploader", info.get("artist", "Unknown"))
                duration = info.get("duration", 0)

                video_id = info.get("id", "unknown")
                filename = os.path.join(DOWNLOADS_DIR, f"{video_id}.mp3")

                if not os.path.exists(filename):
                    base = os.path.join(DOWNLOADS_DIR, video_id)
                    for ext in [".mp3", ".m4a", ".webm", ".opus"]:
                        if os.path.exists(base + ext):
                            filename = base + ext
                            break

                if not os.path.exists(filename):
                    return None, {"error": "Musiqa yuklab olinmadi."}

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
        logger.error(f"Music download error for URL '{url}': {e}")
        return None, {"error": "Musiqa yuklashda xatolik yuz berdi."}


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
