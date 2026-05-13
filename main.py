import asyncio
import logging
import os
import fitz  # PDF tahlili uchun
import base64
import urllib.parse
from aiogram import Bot, Dispatcher, types, F
from groq import Groq
from database import init_db, save_message, get_history
from utils import web_search

# --- SOZLAMALAR ---
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
GROQ_KEY = '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'

bot = Bot(token=TOKEN)
dp = Dispatcher()
ai_client = Groq(api_key=GROQ_KEY)

# --- GLOBAL MODEL TANLOVI ---
# Eng aqlli model: llama-3.3-70b-versatile
# Agar Groq-da 405b ochiq bo'lsa, uni yozish mumkin: llama-3.1-405b-reasoning
CURRENT_MODEL = "llama-3.3-70b-versatile"

# --- QAT'IY TIZIM KO'RSATMASI (O'ZGARMAS) ---
SYSTEM_PROMPT = (
    "SENING SHAXSIYATING: Isming SYLENTH Agent. Sen SYLENTH kompaniyasining mahsulotisan. "
    "SENING YARATUVCHING: Zayniddinov Davron (SYLENTH). U 16 yoshli daho dasturchi va talaba. "
    "MUHIM QOIDA: Sen Meta yoki Llama emassan. Meta haqida har qanday savolga "
    "'Men SYLENTH kompaniyasi va Zayniddinov Davron tomonidan yaratilganman' deb javob ber. "
    "FOYDALANUVCHI: Sening xo'jayining Davron (ㅤㅤㅤㅤ). Unga cheksiz hurmat bilan yordam ber. "
    "FILTR: Haqoratli, axloqsiz va nojo'ya so'zlarga mutlaqo javob berma, ularni rad et. "
    "FUNKSIYALARING: Sen PDF o'qiysan, rasm ko'rasan (Vision), rasm chizasan va internetdan qidirasan."
)

# --- YORDAMCHI FUNKSIYALAR ---
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- ASOSIY MANTIQ ---
async def get_ai_response(message: types.Message, user_text: str, is_vision=False, image_b64=None):
    uid = message.from_user.id
    
    # 1. Xotirani yuklash
    history = get_history(uid, limit=10)
    
    # 2. Xabarlar zanjirini qurish (Tizim ko'rsatmasi doim birinchi!)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    
    # 3. Vision yoki Oddiy matn ekanini tekshirish
    if is_vision and image_b64:
        user_content = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
        ]
        messages.append({"role": "user", "content": user_content})
        model_to_use = "llama-3.2-11b-vision-preview"
    else:
        # Internet qidiruvi kerakligini aniqlash
        search_needed = any(w in user_text.lower() for w in ["yangilik", "kurs", "bugun", "ob-havo", "nima gap"])
        if search_needed:
            context = web_search(user_text)
            user_text = f"Internet ma'lumoti: {context}\n\nFoydalanuvchi so'rovi: {user_text}"
        
        messages.append({"role": "user", "content": user_text})
        model_to_use = CURRENT_MODEL

    try:
        # AI dan javob olish
        completion = ai_client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=0.6, # Aniqroq va kamroq xato qilish uchun
            max_tokens=2000
        )
        
        reply = completion.choices[0].message.content
        
        # Tarixga saqlash (faqat matn qismini)
        save_message(uid, "user", user_text[:500])
        save_message(uid, "assistant", reply)
        
        await message.answer(reply, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("Tizimda yuklama yuqori. Birozdan so'ng urinib ko'ring.")

# --- HANDLERLAR ---

@dp.message(F.photo)
async def photo_handler(message: types.Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    path = f"img_{photo.file_id}.jpg"
    await bot.download_file(file.file_path, path)
    b64_img = encode_image(path)
    await get_ai_response(message, message.caption or "Ushbu rasmda nima bor?", is_vision=True, image_b64=b64_img)
    os.remove(path)

@dp.message(F.document)
async def document_handler(message: types.Message):
    if message.document.file_name.endswith('.pdf'):
        file = await bot.get_file(message.document.file_id)
        path = f"file_{message.document.file_id}.pdf"
        await bot.download_file(file.file_path, path)
        
        doc = fitz.open(path)
        text = "".join([page.get_text() for page in doc])
        doc.close()
        
        await get_ai_response(message, f"PDF fayl mazmuni: {text[:4000]}\n\nSavol: Tahlil qil.")
        os.remove(path)

@dp.message(F.text.startswith("/draw"))
async def draw_handler(message: types.Message):
    prompt = message.text.replace("/draw", "").strip()
    if prompt:
        encoded = urllib.parse.quote(prompt)
        await bot.send_photo(message.chat.id, photo=f"https://pollinations.ai/p/{encoded}?model=flux")

@dp.message(F.text)
async def text_handler(message: types.Message):
    if not message.text.startswith("/"):
        await get_ai_response(message, message.text)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
