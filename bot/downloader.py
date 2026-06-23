"""
Media download module using yt-dlp.
Supports video download from YouTube, Instagram, TikTok, and Facebook.
Supports music search and download from YouTube.

Features:
- Fully async download using run_in_executor
- cookies.txt support for Instagram/Facebook authentication
- 50MB Telegram file size limit enforcement with user-friendly messaging
- Automatic file cleanup after sending
- Multi-stage status updates via callback (Yuklanmoqda -> Botga yuklanmoqda -> Yuborildi)
- Comprehensive error handling with try-except blocks
"""

import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple, Callable, Awaitable

import yt_dlp

logger = logging.getLogger(__name__)

# Configuration
DOWNLOADS_DIR = "downloads"
MAX_FILE_SIZE_MB = 50
COOKIES_FILE = "cookies.txt"

# Maximum number of simultaneous download operations. Requests beyond this
# limit wait until a slot becomes free.
MAX_CONCURRENT_DOWNLOADS = 3
_download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

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

# Platforms that require cookies for access
_COOKIE_PLATFORMS = ["instagram.com", "facebook.com", "fb.watch"]


def _ensure_downloads_dir() -> None:
    """Create downloads directory if it doesn't exist."""
    Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)


def _has_cookies_file() -> bool:
    """Check if cookies.txt file exists for authenticated downloads."""
    return os.path.isfile(COOKIES_FILE)


def _needs_cookies(url: str) -> bool:
    """
    Check if the URL belongs to a platform that may need cookies
    (Instagram, Facebook) for bypassing access restrictions.
    """
    url_lower = url.lower()
    for platform in _COOKIE_PLATFORMS:
        if platform in url_lower:
            return True
    return False


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


def _build_video_ydl_opts(url: str, token: str) -> dict:
    """
    Build yt-dlp options for video download.
    Includes cookies.txt if available and the URL is for Instagram/Facebook.

    Args:
        url: The video URL to build options for
        token: Per-invocation unique token used in the output template so that
               concurrent downloads of the same media id never collide

    Returns:
        dict of yt-dlp options
    """
    opts = {
        "format": "best[ext=mp4][filesize<50M]/best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "outtmpl": os.path.join(DOWNLOADS_DIR, f"%(id)s.{token}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
        "merge_output_format": "mp4",
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
    }

    # Add cookies for platforms that require authentication
    if _needs_cookies(url) and _has_cookies_file():
        opts["cookiefile"] = COOKIES_FILE
        logger.info(f"Using cookies.txt for: {url}")

    return opts


def _build_music_ydl_opts(use_cookies: bool = False, token: str = "") -> dict:
    """
    Build yt-dlp options for music download (audio extraction).

    Args:
        use_cookies: Whether to include cookies.txt
        token: Per-invocation unique token used in the output template so that
               concurrent downloads of the same media id never collide

    Returns:
        dict of yt-dlp options
    """
    suffix = f".{token}" if token else ""
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOADS_DIR, f"%(id)s{suffix}.%(ext)s"),
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

    if use_cookies and _has_cookies_file():
        opts["cookiefile"] = COOKIES_FILE

    return opts


async def download_video(
    url: str,
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> Tuple[Optional[str], str]:
    """
    Download a video from a supported platform using yt-dlp.

    Provides multi-stage progress updates via status_callback:
    - Stage 1: "Yuklanmoqda..." (downloading from platform)
    - Stage 2: "Botga yuklanmoqda..." (preparing to send)
    - Stage 3: Complete (returns file path)

    Enforces 50MB Telegram file size limit.
    Uses cookies.txt for Instagram/Facebook if available.

    Args:
        url: Video URL to download
        status_callback: Optional async function to call with status text updates.
                        Signature: async def callback(status_text: str) -> None

    Returns:
        Tuple of (file_path, title) on success, or (None, error_message) on failure
    """
    _ensure_downloads_dir()

    # Stage 1: Starting download
    if status_callback:
        try:
            await status_callback("📹 Video yuklanmoqda... ⏳")
        except Exception:
            pass

    ydl_opts = _build_video_ydl_opts(url, token=uuid.uuid4().hex[:8])

    try:

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, "Video ma'lumotlarini olishda xatolik."

                title = info.get("title", "Video")
                filename = ydl.prepare_filename(info)

                # Handle merged files - yt-dlp may change extension
                if not os.path.exists(filename):
                    base = os.path.splitext(filename)[0]
                    filename = base + ".mp4"

                if not os.path.exists(filename):
                    # Try webm as well
                    base = os.path.splitext(filename)[0]
                    for ext in [".mp4", ".webm", ".mkv"]:
                        candidate = base + ext
                        if os.path.exists(candidate):
                            filename = candidate
                            break

                if not os.path.exists(filename):
                    return None, "Video yuklab olinmadi."

                # Check file size against Telegram limit
                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.remove(filename)
                    return None, (
                        f"⚠️ Video hajmi juda katta ({file_size_mb:.1f} MB).\n"
                        f"Telegram cheklovi: {MAX_FILE_SIZE_MB} MB.\n\n"
                        "💡 Tavsiya: Videoni sifatini pasaytirib yuklash uchun "
                        "havola oxiriga '720p' yoki '480p' yozing, yoki "
                        "qisqaroq video tanlang."
                    )

                return filename, title

        async with _download_semaphore:
            result = await asyncio.to_thread(_download)

        # Stage 2: Download complete, preparing to send
        if result[0] is not None and status_callback:
            try:
                await status_callback("📤 Botga yuklanmoqda... ⏳")
            except Exception:
                pass

        return result

    except Exception as e:
        logger.error(f"Video download error for {url}: {e}")
        error_msg = str(e)

        if "Unsupported URL" in error_msg:
            return None, "Bu havola qo'llab-quvvatlanmaydi."
        elif "Private video" in error_msg or "Sign in" in error_msg:
            if _needs_cookies(url) and not _has_cookies_file():
                return None, (
                    "Bu video yopiq (private). Yuklab olish uchun "
                    "cookies.txt fayli kerak. Admin bilan bog'laning."
                )
            return None, "Bu video yopiq (private) - yuklab bo'lmaydi."
        elif "login" in error_msg.lower() or "cookie" in error_msg.lower():
            if not _has_cookies_file():
                return None, (
                    "Bu platformadan yuklab olish uchun cookies.txt kerak.\n"
                    "Admin cookies.txt faylini serverga joylashi kerak."
                )
            return None, "Avtorizatsiya xatoligi. Cookies eskirgan bo'lishi mumkin."
        elif "unavailable" in error_msg.lower():
            return None, "Video mavjud emas yoki o'chirilgan."
        elif "too many requests" in error_msg.lower() or "429" in error_msg:
            return None, "Platforma so'rovlar sonini chekladi. Biroz kutib, qayta urinib ko'ring."
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

        results = await asyncio.to_thread(_search)
        return results

    except Exception as e:
        logger.error(f"Music search error for query '{query}': {e}")
        return []


async def download_music(
    query: str,
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> Tuple[Optional[str], dict]:
    """
    Search YouTube for music by query and download as MP3.

    Args:
        query: Music search query (song name, artist, etc.)
        status_callback: Optional async function for status updates

    Returns:
        Tuple of (file_path, metadata_dict) on success,
        or (None, error_dict) on failure
    """
    _ensure_downloads_dir()

    # Stage 1: Searching and downloading
    if status_callback:
        try:
            await status_callback("🎵 Musiqa qidirilmoqda va yuklanmoqda... ⏳")
        except Exception:
            pass

    token = uuid.uuid4().hex[:8]
    ydl_opts = _build_music_ydl_opts(use_cookies=False, token=token)
    ydl_opts["default_search"] = "ytsearch1"

    try:

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

                # Derive the collision-safe base name from the output template
                # and locate the post-processed audio file.
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                filename = base + ".mp3"

                if not os.path.exists(filename):
                    # Try other possible extensions after the postprocessor
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
                    return None, {
                        "error": (
                            f"Fayl hajmi juda katta ({file_size_mb:.1f} MB). "
                            f"Telegram cheklovi: {MAX_FILE_SIZE_MB} MB."
                        )
                    }

                metadata = {
                    "title": title,
                    "artist": artist,
                    "duration": duration,
                }

                return filename, metadata

        async with _download_semaphore:
            result = await asyncio.to_thread(_download)

        # Stage 2: Ready to send
        if result[0] is not None and status_callback:
            try:
                await status_callback("📤 Botga yuklanmoqda... ⏳")
            except Exception:
                pass

        return result

    except Exception as e:
        logger.error(f"Music download error for query '{query}': {e}")
        return None, {"error": "Musiqa yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."}


async def download_music_by_url(
    url: str,
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> Tuple[Optional[str], dict]:
    """
    Download music from a specific YouTube URL as MP3.

    Args:
        url: YouTube video URL
        status_callback: Optional async function for status updates

    Returns:
        Tuple of (file_path, metadata_dict) on success,
        or (None, error_dict) on failure
    """
    _ensure_downloads_dir()

    # Stage 1: Downloading
    if status_callback:
        try:
            await status_callback("🎵 Musiqa yuklanmoqda... ⏳")
        except Exception:
            pass

    use_cookies = _needs_cookies(url)
    token = uuid.uuid4().hex[:8]
    ydl_opts = _build_music_ydl_opts(use_cookies=use_cookies, token=token)

    try:

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if info is None:
                    return None, {"error": "Musiqa topilmadi."}

                title = info.get("title", "Unknown")
                artist = info.get("uploader", info.get("artist", "Unknown"))
                duration = info.get("duration", 0)

                # Derive the collision-safe base name from the output template
                # and locate the post-processed audio file.
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                filename = base + ".mp3"

                if not os.path.exists(filename):
                    for ext in [".mp3", ".m4a", ".webm", ".opus"]:
                        if os.path.exists(base + ext):
                            filename = base + ext
                            break

                if not os.path.exists(filename):
                    return None, {"error": "Musiqa yuklab olinmadi."}

                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.remove(filename)
                    return None, {
                        "error": (
                            f"Fayl hajmi juda katta ({file_size_mb:.1f} MB). "
                            f"Telegram cheklovi: {MAX_FILE_SIZE_MB} MB."
                        )
                    }

                metadata = {
                    "title": title,
                    "artist": artist,
                    "duration": duration,
                }

                return filename, metadata

        async with _download_semaphore:
            result = await asyncio.to_thread(_download)

        # Stage 2: Ready to send
        if result[0] is not None and status_callback:
            try:
                await status_callback("📤 Botga yuklanmoqda... ⏳")
            except Exception:
                pass

        return result

    except Exception as e:
        logger.error(f"Music download error for URL '{url}': {e}")
        return None, {"error": "Musiqa yuklashda xatolik yuz berdi."}


def cleanup_file(path: str) -> None:
    """
    Remove a file after it has been sent.
    Ensures server disk space is freed.

    Args:
        path: Path to the file to remove
    """
    try:
        if path and os.path.exists(path):
            os.remove(path)
            logger.debug(f"Cleaned up file: {path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup file {path}: {e}")


def cleanup_stale_downloads() -> None:
    """
    Remove leftover files in the downloads directory from previous runs.

    Called on startup so the bot never accumulates stale media files. Missing
    directory is a no-op; per-file removal failures are logged and skipped.
    """
    d = Path(DOWNLOADS_DIR)
    if not d.exists():
        return
    for f in d.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except OSError as exc:
                logger.warning("Could not remove stale file %s: %s", f.name, exc)
