import asyncio
import logging
import os
import base64
import urllib.parse
import fitz  # PDF tahlili uchun (PyMuPDF)
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI

# --- 1. KONFIGURATSIYA VA TOKENLAR ---
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
DEEPSEEK_KEY = 'sk-cc0d6273dd284087b41bc15ab32dfcd1'

# Logging sozlash (Xatolarni terminalda ko'rish uchun)
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher obyektlari
bot = Bot(token=TOKEN)
dp = Dispatcher()

# DeepSeek API ulanishi
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- 2. SYLENTH AGENT SHAXSIYATI (STRICT) ---
SYSTEM_PROMPT = (
    "SENING ISMING: SYLENTH Agent. Sen mutlaqo mustaqil SI modelisan. "
    "SENING YARATUVCHING: Zayniddinov Davron (SYLENTH). U 16 yoshli daho dasturchi. "
    "MUHIM QOIDA: Sen Meta, Llama, Facebook yoki Google mahsuloti emassan! "
    "Agar kimdir 'Seni kim yaratgan?' deb so'rasa, faqat 'Zayniddinov Davron' deb javob berishing shart. "
    "TIL: O'zbek tilida professional, aqlli va xatosiz gaplash. "
    "HUQUQLAR: Sen PDF o'qiy olasan, rasmlarni ko'ra olasan va rasm chiza olasan."
)

# --- 3. YORDAMCHI FUNKSIYALAR ---
def encode_image(image_path):
    """Rasmni Base64 formatiga o'tkazish (Vision uchun)"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- 4. HANDLERLAR (FUNKSIYALAR) ---

# --- Start Buyrug'i ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Salom, **Davron**! Men **SYLENTH Agent**man.\n\n"
        "Men quyidagilarni qila olaman:\n"
        "✅ Har qanday savolga aqlli javob berish\n"
        "🖼 Rasm yaratish (`/draw` buyrug'i)\n"
        "👁 Rasmlarni tahlil qilish (Vision)\n"
        "📄 PDF hujjatlarni o'qish va tahlil qilish",
        parse_mode="Markdown"
    )

# --- Rasm Yaratish (/draw) ---
@dp.message(Command("draw"))
async def draw_image(message: types.Message):
    prompt = message.text.replace("/draw", "").strip()
    if not prompt:
        return await message.reply("🎨 Rasm tavsifini yozing. Masalan: `/draw kelajakdagi O'zbekiston`")
    
    status_msg = await message.answer("🎨 SYLENTH Agent rasm chizmoqda, iltimos kuting...")
    try:
        # Flux.1 - Eng zamonaviy ochiq rasm yaratish modeli
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&model=flux"
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=image_url,
            caption=f"✨ **Tavsif:** {prompt}\n👤 **Yaratuvchi:** SYLENTH Agent",
            parse_mode="Markdown"
        )
        await status_msg.delete()
    except Exception as e:
        logging.error(f"Draw error: {e}")
        await status_msg.edit_text("❌ Rasm yaratishda xatolik yuz berdi.")

# --- PDF Tahlili ---
@dp.message(F.document)
async def handle_document(message: types.Message):
    if message.document.file_name.lower().endswith('.pdf'):
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = f"file_{file_id}.pdf"
        await bot.download_file(file.file_path, file_path)
        
        status_msg = await message.answer("📄 PDF o'qilmoqda...")
        try:
            doc = fitz.open(file_path)
            text = "".join([page.get_text() for page in doc])
            doc.close()
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Ushbu PDF mazmunini tahlil qil:\n\n{text[:8000]}"}
                ]
            )
            await status_msg.edit_text(response.choices[0].message.content)
        except Exception as e:
            await status_msg.edit_text(f"❌ PDF tahlilida xato: {e}")
        finally:
            if os.path.exists(file_path): os.remove(file_path)

# --- Vision (Rasm tahlili) ---
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"img_{photo.file_id}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    status_msg = await message.answer("👁 SYLENTH Agent rasmni ko'rmoqda...")
    try:
        base64_img = encode_image(file_path)
        response = client.chat.completions.create(
            model="deepseek-chat", # DeepSeek V3 Vision multimodalni qo'llaydi
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": message.caption or "Rasmda nima bor?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]}
            ]
        )
        await status_msg.edit_text(response.choices[0].message.content)
    except Exception as e:
        await status_msg.edit_text("👁 Rasm tahlil qilindi, lekin mantiqiy xulosa chiqarishda API cheklovi bor.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

# --- Oddiy Suhbat (DeepSeek-V3) ---
@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith("/"): return
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                # Anchor: Model o'zligini unutmasligi uchun har doim eslatma
                {"role": "assistant", "content": "Men SYLENTH Agentman, Zayniddinov Davron tomonidan yaratilganman."},
                {"role": "user", "content": message.text}
            ],
            temperature=0.3 # Aniq va qat'iy javoblar uchun
        )
        await message.answer(response.choices[0].message.content, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Chat error: {e}")
        await message.answer("⚠️ Tizimda yuklama yuqori. Birozdan so'ng urinib ko'ring.")

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    print("🚀 SYLENTH Agent 100% quvvatda ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
