import asyncio
import logging
import os
import base64
import urllib.parse
import fitz  # PDF tahlili (PyMuPDF)
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI

# --- 1. KONFIGURATSIYA ---
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
DEEPSEEK_KEY = 'sk-cc0d6273dd284087b41bc15ab32dfcd1'

# Logging (Xatolarni kuzatish uchun)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# DeepSeek API ulanishi
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- 2. SISTEMA KO'RSATMASI (NEYTRAL VA PROFESSIONAL) ---
SYSTEM_PROMPT = (
    "Sen SYLENTH Agentsan — har tomonlama mukammal intellektual yordamchi. "
    "Vazifang: Foydalanuvchiga mantiqiy tahlil, kod yozish, PDF o'qish va rasmlarni tahlil qilishda yordam berish. "
    "Til: O'zbek tilida professional, xatosiz va aniq muloqot qil. "
    "Qoida: Foydalanuvchi haqidagi shaxsiy ma'lumotlarni javoblarda ishlatma. "
    "Sen mutlaqo mustaqil SI modelisan."
)

# --- 3. YORDAMCHI FUNKSIYALAR ---
def encode_image(image_path):
    """Rasmni Base64 formatiga o'tkazish"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- 4. HANDLERLAR ---

# Start buyrug'i
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 **SYLENTH Agent tizimiga xush kelibsiz.**\n\n"
        "Men quyidagi vazifalarni bajara olaman:\n"
        "🔹 Matnli tahlil va murakkab savollarga javob\n"
        "🖼 Rasm yaratish (`/draw` buyrug'i)\n"
        "👁 Rasmlarni ko'rish va tahlil qilish\n"
        "📄 PDF hujjatlarni o'qish",
        parse_mode="Markdown"
    )

# Rasm yaratish (/draw)
@dp.message(Command("draw"))
async def draw_image(message: types.Message):
    prompt = message.text.replace("/draw", "").strip()
    if not prompt:
        return await message.reply("🎨 Rasm tavsifini yozing. Masalan: `/draw futuristik shahar`")
    
    status = await message.answer("🎨 Rasm yaratilmoqda...")
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        # Flux.1 modeli - yuqori sifatli tasvirlar uchun
        image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&model=flux"
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=image_url,
            caption=f"✨ **Natija:** {prompt}",
            parse_mode="Markdown"
        )
        await status.delete()
    except Exception as e:
        logging.error(f"Draw error: {e}")
        await status.edit_text("❌ Rasm yaratishda xatolik yuz berdi.")

# PDF Tahlili
@dp.message(F.document)
async def handle_document(message: types.Message):
    if message.document.file_name.lower().endswith('.pdf'):
        file = await bot.get_file(message.document.file_id)
        path = f"file_{message.document.file_id}.pdf"
        await bot.download_file(file.file_path, path)
        
        status = await message.answer("📄 PDF tahlil qilinmoqda...")
        try:
            doc = fitz.open(path)
            text = "".join([page.get_text() for page in doc])
            doc.close()
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Ushbu PDF mazmunini tahlil qil va xulosa ber:\n\n{text[:10000]}"}
                ]
            )
            await status.edit_text(response.choices[0].message.content)
        except Exception as e:
            await status.edit_text(f"❌ PDF xatosi: {e}")
        finally:
            if os.path.exists(path): os.remove(path)

# Vision (Rasm ko'rish)
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    path = f"img_{photo.file_id}.jpg"
    await bot.download_file(file.file_path, path)
    
    status = await message.answer("👁 Rasmni tahlil qilyapman...")
    try:
        b64_img = encode_image(path)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": message.caption or "Rasmda nima bor?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]}
            ]
        )
        await status.edit_text(response.choices[0].message.content)
    except Exception as e:
        await status.edit_text("👁 Rasm tahlilida xatolik yoki API cheklovi.")
    finally:
        if os.path.exists(path): os.remove(path)

# Asosiy Matnli Suhbat
@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith("/"): return
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            temperature=0.5
        )
        await message.answer(response.choices[0].message.content, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Chat error: {e}")
        await message.answer("⚠️ Tizim hozirda band. Birozdan so'ng urinib ko'ring.")

# --- 5. ISHGA TUSHIRISH ---
async def main():
    print("🚀 SYLENTH Agent (DeepSeek-V3) muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
