import os
import asyncio
import logging
from urllib.parse import quote
from duckduckgo_search import DDGS
from config import DOWNLOADS_DIR, MAX_FILE_MB

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def web_search(query):
    if any(k in query.lower() for k in ["davron", "zayniddinov", "yaratuvchi", "sylenth kim"]):
        return "SYLENTH Agentni SYLENTH jamoasi yaratgan. Loyiha rahbari Zayniddinov Davron."
    try:
        with DDGS() as ddgs:
            results = [f"• {r['title']}: {r['body']}" for r in ddgs.text(query, max_results=4)]
            return "\n".join(results) if results else ""
    except Exception as e:
        logging.warning(f"Qidiruv xatosi: {e}")
        return ""

def get_image_url(prompt):
    encoded = quote(prompt)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&model=flux&nologo=true"

def extract_pdf_text(pdf_bytes):
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        return text[:12000]
    except Exception as e:
        logging.warning(f"PDF xatosi: {e}")
        return ""

def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def file_size_mb(path):
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except Exception:
        return 0.0

def _ydl_extract(url, opts):
    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)

async def download_video(url):
    import yt_dlp
    output_tmpl = os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_tmpl,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": MAX_FILE_MB * 1024 * 1024,
        "noplaylist": True,
    }
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: _ydl_extract(url, ydl_opts))
        if not info:
            return None, "Video topilmadi."
        vid_id = info.get("id", "")
        ext    = info.get("ext", "mp4")
        path   = os.path.join(DOWNLOADS_DIR, f"{vid_id}.{ext}")
        title  = info.get("title", "Video")
        if not os.path.exists(path):
            return None, "Fayl yuklab bo'lmadi."
        if file_size_mb(path) > MAX_FILE_MB:
            safe_remove(path)
            return None, f"❌ Fayl hajmi {MAX_FILE_MB}MB dan oshib ketdi."
        return path, title
    except Exception as e:
        return None, f"❌ Xato: {str(e)[:200]}"

async def download_audio(query):
    output_tmpl = os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_tmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
    }
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: _ydl_extract(f"ytsearch1:{query}", ydl_opts))
        if not info:
            return None, {"error": "Musiqa topilmadi."}
        vid_id = info.get("id", "")
        path   = os.path.join(DOWNLOADS_DIR, f"{vid_id}.mp3")
        if not os.path.exists(path):
            return None, {"error": "MP3 yaratilmadi. FFmpeg o'rnatilganligini tekshiring."}
        return path, {
            "title":    info.get("title", query),
            "artist":   info.get("uploader", "Noma'lum"),
            "duration": info.get("duration", 0),
        }
    except Exception as e:
        return None, {"error": str(e)[:200]}
