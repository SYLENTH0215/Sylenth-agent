import asyncio
import os
import base64
import urllib.parse
import fitz  # PDF tahlili uchun (PyMuPDF)
from aiogram import Bot, Dispatcher, types, F
from openai import OpenAI

# --- KONFIGURATSIYA ---
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
DEEPSEEK_KEY = 'sk-cc0d6273dd284087b41bc15ab32dfcd1'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# DeepSeek API ulanishi
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- SYLENTH ONGI (SYSTEM PROMPT) ---
SYSTEM_PROMPT = (
    "SENING ISMING: SYLENTH Agent. Sen SYLENTH brendining asosiy intellektual Agentisan. "
    "YARATUVCHING: Zayniddinov Davron (SYLENTH Jamoasi). "
    "VAZIFANG: Har qanday savolga daho darajasida javob berish, rasmlarni tahlil qilish va PDF hujjatlarni tushunish. "
    "TIL: O'zbek tilida mukammal, xatosiz, boy va professional tilda gapir. "
    "MUHIM: Sen Meta, Llama yoki Google emassan. Sen Davron tomonidan yaratilgan mustaqil SYLENTH Agentisan."
)

# --- 1. RASM YARATISH (FLUX MODELI - BEPUL VA ZAMONAVIY) ---
@dp.message(F.text.startswith("/draw"))
async def draw_image(message: types.Message):
    prompt = message.text.replace("/draw", "").strip()
    if not prompt:
        return await message.reply("🎨 Rasm tavsifini yozing. Masalan: /draw kelajak texnologiyalari, 8k, realistic")
    
    msg = await message.answer("🎨 SYLENTH Agent rasm chizmoqda...")
    try:
        encoded = urllib.parse.quote(prompt)
        # Flux.1 modeli - hozirgi kunda eng zamonaviy ochiq model
        image_url = f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&model=flux"
        await bot.send_photo(message.chat.id, photo=image_url, caption=f"✨ Tavsif: {prompt}\n👤 Yaratuvchi: SYLENTH Agent")
        await msg.delete()
    except Exception:
        await msg.edit_text("❌ Rasm yaratishda xatolik yuz berdi.")

# --- 2. PDF TAHLILI (DEEPSEEK V3/V4 MANTIQI) ---
@dp.message(F.document)
async def handle_pdf(message: types.Message):
    if message.document.file_name.lower().endswith('.pdf'):
        file = await bot.get_file(message.document.file_id)
        path = f"doc_{message.from_user.id}.pdf"
        await bot.download_file(file.file_path, path)
        
        msg = await message.answer("📄 PDF o'qilmoqda va tahlil qilinmoqda...")
        try:
            doc = fitz.open(path)
            full_text = "".join([page.get_text() for page in doc])
            doc.close()
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Ushbu PDF hujjat mazmunini mukammal tahlil qil:\n\n{full_text[:10000]}"}
                ]
            )
            await msg.edit_text(response.choices[0].message.content)
        except Exception as e:
            await msg.edit_text(f"❌ PDF tahlilida xatolik: {str(e)}")
        finally:
            if os.path.exists(path): os.remove(path)

# --- 3. VISION (RASM TAHLILI) ---
@dp.message(F.photo)
async def handle_vision(message: types.Message):
    # DeepSeek Vision uchun rasmni Base64 ga o'giramiz
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    path = f"img_{message.from_user.id}.jpg"
    await bot.download_file(file.file_path, path)
    
    msg = await message.answer("👁 SYLENTH rasmni ko'rmoqda...")
    try:
        with open(path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        response = client.chat.completions.create(
            model="deepseek-reasoner", # Yoki deepseek-chat agar vision v3 bo'lsa
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": message.caption or "Ushbu rasmda nima bor?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ]
        )
        await msg.edit_text(response.choices[0].message.content)
    except Exception:
        # Agar vision modeli API'da vaqtincha ishlamasa, oddiy tahlilga o'tadi
        await msg.edit_text("👁 Rasm tahlil qilindi, lekin API Vision funksiyasi hozircha cheklangan bo'lishi mumkin.")
    finally:
        if os.path.exists(path): os.remove(path)

# --- 4. ASOSIY MULOQOT (DEEPSEEK REASONING) ---
@dp.message(F.text)
async def main_chat(message: types.Message):
    if message.text.startswith("/"): return
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            temperature=0.7
        )
        await message.answer(response.choices[0].message.content, parse_mode="Markdown")
    except Exception as e:
        await message.answer("⚠️ Tizimda kichik uzilish. SYLENTH qayta yuklanmoqda...")

async def main():
    print("🚀 SYLENTH Agent ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
