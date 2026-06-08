import os
import asyncio
import logging
from urllib.parse import quote
from config import DOWNLOADS_DIR, MAX_FILE_MB

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def web_search(query):
    """DuckDuckGo orqali veb qidiruv"""
    try:
        # SYLENTH haqida so'rovlar uchun maxsus javob
        if any(k in query.lower() for k in ["davron", "zayniddinov", "yaratuvchi", "sylenth kim", "creator"]):
            return "🤖 <b>SYLENTH Agent</b> — SYLENTH jamoasi tomonidan yaratilgan sun'iy intellekt yordamchisi.\n\n👨‍💼 Loyiha rahbari: <b>Zayniddinov Davron</b>\n\n🔗 Tosh davlat texnika universiteti"
        
        # DuckDuckGo qidiruv
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=5):
                title = r.get('title', 'Sarlavha yo\'q')[:100]
                body = r.get('body', 'Tavsif yo\'q')[:150]
                results.append(f"<b>📌 {title}</b>\n{body}\n")
            
            return "\n".join(results) if results else "❌ Qidiruv natijalari topilmadi."
    except Exception as e:
        logging.warning(f"Qidiruv xatosi: {e}")
        return "⚠️ Qidiruv xatosi yuz berdi. Keyinroq urinib ko'ring."

def get_image_url(prompt):
    """Pollinations.ai orqali rasm havolasini yaratish"""
    try:
        encoded = quote(prompt)
        return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&model=flux&nologo=true"
    except Exception as e:
        logging.error(f"Rasm URL xatosi: {e}")
        return ""

def extract_pdf_text(pdf_bytes):
    """PDF-dan matn chiqarish"""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text[:12000]  # Birinchi 12000 belgini qaytarish
    except Exception as e:
        logging.warning(f"PDF xatosi: {e}")
        return ""

def safe_remove(path):
    """Fayl xavfsiz o'chirish"""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logging.warning(f"Fayl o'chirish xatosi: {e}")

def file_size_mb(path):
    """Fayl hajmini megabyte da qaytarish"""
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except Exception:
        return 0.0

def _ydl_extract(url, opts):
    """yt-dlp bilan video ma'lumotlarini chiqarish (sinx)"""
    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)

async def download_video(url):
    """YouTubedan yoki boshqa saytdan video yuklash"""
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
            return None, "❌ Video topilmadi."
        
        vid_id = info.get("id", "")
        ext    = info.get("ext", "mp4")
        path   = os.path.join(DOWNLOADS_DIR, f"{vid_id}.{ext}")
        title  = info.get("title", "Video")
        
        if not os.path.exists(path):
            return None, "❌ Fayl yuklab bo'lmadi."
        
        if file_size_mb(path) > MAX_FILE_MB:
            safe_remove(path)
            return None, f"❌ Fayl hajmi {MAX_FILE_MB}MB dan oshib ketdi."
        
        return path, title
    except Exception as e:
        return None, f"❌ Xato: {str(e)[:200]}"

async def download_audio(query):
    """YouTube-dan audio/musiqa yuklash"""
    import yt_dlp
    
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
            return None, {"error": "❌ Musiqa topilmadi."}
        
        vid_id = info.get("id", "")
        path   = os.path.join(DOWNLOADS_DIR, f"{vid_id}.mp3")
        
        if not os.path.exists(path):
            return None, {"error": "❌ MP3 yaratilmadi. FFmpeg o'rnatilganligini tekshiring."}
        
        return path, {
            "title":    info.get("title", query),
            "artist":   info.get("uploader", "Noma'lum"),
            "duration": info.get("duration", 0),
        }
    except Exception as e:
        logging.error(f"Audio yuklab olish xatosi: {e}")
        return None, {"error": f"❌ Xato: {str(e)[:200]}"}
