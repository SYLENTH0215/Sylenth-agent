import asyncio
import logging
import os
import fitz  # PyMuPDF
import urllib.parse
from aiogram import Bot, Dispatcher, types, F
from groq import Groq
from database import init_db, save_message, get_history
from utils import web_search, encode_image

# --- SOZLAMALAR ---
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
GROQ_KEY = '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'

bot = Bot(token=TOKEN)
dp = Dispatcher()
ai_client = Groq(api_key=GROQ_KEY)

SYSTEM_PROMPT = (
    "Sen SYLENTH Agentsan, agar foydalanuvchi seni yaratgan shaxs haqida soʻragan taqdirdagina Yaratuvching: Zayniddinov Davron - deb javob ber. "
    "Sen shaxsiy yordamchi va aqlli do'stsan. Meta haqida gapirma. "
    "Javoblaring batafsil, aniq va yolg'onsiz bo'lsin va notoʻlri malumotlarni umuman tarqatma va aytma."
)

# --- RASM CHIZISH (/draw) ---
@dp.message(F.text.startswith("/draw"))
async def draw_handler(message: types.Message):
    prompt = message.text.replace("/draw", "").strip()
    if not prompt:
        return await message.reply("Tavsif yozing. Masalan: /draw kosmosdagi robot")
    
    encoded_prompt = urllib.parse.quote(prompt)
    img_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&model=flux"
    await bot.send_photo(message.chat.id, photo=img_url, caption=f"🎨: {prompt}")

# --- RASM TAHLILI (Vision) ---
@dp.message(F.photo)
async def vision_handler(message: types.Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    path = f"{photo.file_id}.jpg"
    await bot.download_file(file.file_path, path)
    
    try:
        base64_img = encode_image(path)
        completion = ai_client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": message.caption or "Bu rasmda nima bor?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
            ]}]
        )
        await message.reply(completion.choices[0].message.content)
    finally:
        if os.path.exists(path): os.remove(path)

# --- PDF VA HUJJATLAR ---
@dp.message(F.document)
async def doc_handler(message: types.Message):
    file = await bot.get_file(message.document.file_id)
    path = f"downloads/{message.document.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await bot.download_file(file.file_path, path)
    
    text = ""
    if path.endswith('.pdf'):
        doc = fitz.open(path)
        text = "".join([page.get_text() for page in doc])
        doc.close()
    
    if text:
        await get_ai_response(message, f"Hujjat mazmuni: {text[:3000]}\nSavol: {message.caption or 'Tahlil qil'}")
    os.remove(path)

# --- OVOZLI XABARLAR (STT) ---
@dp.message(F.voice)
async def voice_handler(message: types.Message):
    file = await bot.get_file(message.voice.file_id)
    path = "voice.ogg"
    await bot.download_file(file.file_path, path)
    
    with open(path, "rb") as f:
        trans = ai_client.audio.transcriptions.create(file=(path, f.read()), model="whisper-large-v3")
    
    message.text = trans.text
    await text_handler(message)
    os.remove(path)

# --- ASOSIY MATN QAYTA ISHLOVCHI ---
async def get_ai_response(message, user_text):
    uid = message.from_user.id
    history = get_history(uid)
    if not history: history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Internet qidiruvi kerakmi?
    context = ""
    if any(w in user_text.lower() for w in ["yangilik", "kurs", "bugun", "ob-havo"]):
        context = web_search(user_text)
    
    final_text = f"Internet: {context}\n\nFoydalanuvchi: {user_text}" if context else user_text
    history.append({"role": "user", "content": final_text})
    
    resp = ai_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=history)
    ai_msg = resp.choices[0].message.content
    
    save_message(uid, "user", user_text)
    save_message(uid, "assistant", ai_msg)
    await message.answer(ai_msg, parse_mode="Markdown")

@dp.message(F.text)
async def text_handler(message: types.Message):
    if not message.text.startswith("/"):
        await get_ai_response(message, message.text)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
