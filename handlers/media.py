import os
import logging
from aiogram import Router, types
from utils import download_video, download_audio, get_image_url, safe_remove, file_size_mb
from config import MAX_FILE_MB

# main.py ichidagi AttributeError xatosini oldini olish uchun router yaratamiz
router = Router()

async def send_image(message: types.Message, prompt: str):
    status = await message.answer("🎨 Rasm yaratilmoqda... (10-30 soniya)")
    url = get_image_url(prompt)
    try:
        await message.answer_photo(
            url,
            caption=f"✨ <b>{prompt[:200]}</b>\n\n<i>SYLENTH Image Engine</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Rasm xatosi: {e}")
        await message.answer(f"⚠️ Rasm yuborish xatosi.\n🔗 {url}")
    finally:
        await status.delete()

async def download_and_send_music(message: types.Message, query: str):
    status = await message.answer(f"🎵 <b>{query}</b> qidirilmoqda...", parse_mode="HTML")
    path, meta = await download_audio(query)
    if path is None:
        await status.delete()
        return await message.answer(f"❌ {meta.get('error', 'Musiqa topilmadi.')}")
    if file_size_mb(path) > MAX_FILE_MB:
        safe_remove(path)
        await status.delete()
        return await message.answer(f"❌ Fayl hajmi juda katta.")
    await status.delete()
    send_status = await message.answer("📤 Yuklanmoqda...")
    try:
        with open(path, "rb") as f:
            await message.answer_audio(
                f,
                title=meta.get("title", query)[:64],
                performer=meta.get("artist", "SYLENTH Music")[:32],
                duration=int(meta.get("duration", 0)),
                caption=f"🎵 <b>{meta.get('title', query)[:200]}</b>\n<i>SYLENTH Music Hub</i>",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Audio yuborish xatosi: {e}")
        await message.answer("⚠️ Audio yuborishda xato.")
    finally:
        safe_remove(path)
        await send_status.delete()

async def smart_download(message: types.Message, url: str):
    url = url.strip()
    music_kw = ["musiqa", "music", "qo'shiq", "song", "mp3"]
    if any(k in url.lower() for k in music_kw) and "http" not in url:
        return await download_and_send_music(message, url)

    video_sites = ["youtube.com", "youtu.be", "tiktok.com", "instagram.com",
                   "twitter.com", "x.com", "facebook.com"]
    if not (url.startswith("http") and any(s in url for s in video_sites)):
        return await message.answer(
            "📥 <b>Media yuklash:</b>\n\n"
            "• Video link yuboring (YouTube, TikTok, Instagram, X)\n"
            "• Musiqa: <code>/music qo'shiq nomi</code>",
            parse_mode="HTML"
        )

    status = await message.answer("⬇️ Video yuklanmoqda...")
    path, info = await download_video(url)
    if path is None:
        await status.delete()
        return await message.answer(f"❌ {info}")
    await status.delete()
    send_status = await message.answer("📤 Yuborilmoqda...")
    try:
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            if ext in (".mp4", ".mkv", ".webm", ".mov"):
                await message.answer_video(
                    f, caption=f"🎬 <b>{info[:200]}</b>\n<i>SYLENTH Media Hub</i>",
                    parse_mode="HTML", supports_streaming=True
                )
            else:
                await message.answer_document(
                    f, caption=f"📎 <b>{info[:200]}</b>\n<i>SYLENTH Media Hub</i>",
                    parse_mode="HTML"
                )
    except Exception as e:
        logging.error(f"Video yuborish xatosi: {e}")
        await message.answer("⚠️ Video yuborishda xato.")
    finally:
        safe_remove(path)
        await send_status.delete()
