import os
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from openai import OpenAI
from database import save_message, get_history
from utils import web_search, encode_image_bytes, extract_pdf_text, get_image_url
from states import UserMode

router = Router()

# --- KONFIGURATSIYA (API kalit to'g'ridan-to'g'ri ulandi) ---
DEEPSEEK_KEY = "sk-c5ecf085378146fea99fff7b49cc5b93"
client = OpenAI(
    api_key=DEEPSEEK_KEY,
    base_url="https://api.deepseek.com"
)

SYSTEM_PROMPT = (
    "Sen SYLENTH Agent — Zayniddinov Davron tomonidan yaratilgan "
    "eng zamonaviy AI yordamchisan. O'zbek tilida mukammal, professional "
    "va qisqa javob ber. Keraksiz takrorlashlardan qoching."
)

# --- DeepSeek umumiy funksiya ---
async def ask_deepseek(
    message: types.Message,
    user_text: str,
    model: str = "deepseek-chat",
    extra_context: str = ""
):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Xabarni bazaga saqlash
    try:
        save_message(chat_id, user_id, "user", user_text)
        history = get_history(chat_id)
    except Exception:
        history = [] # Baza bilan muammo bo'lsa, suhbat davom etaveradi

    messages_list = [{"role": "system", "content": SYSTEM_PROMPT}]
    if extra_context:
        messages_list.append({"role": "system", "content": extra_context})
    
    # Tarixni qo'shish
    messages_list += history

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages_list,
            max_tokens=2048
        )
        reply = response.choices[0].message.content
        
        # Javobni bazaga saqlash
        try:
            save_message(chat_id, user_id, "assistant", reply)
        except: pass

        await message.answer(reply, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ API xatosi: <code>{e}</code>", parse_mode="HTML")

# --- Oddiy matn ---
@router.message(UserMode.chat, F.text)
async def handle_chat(message: types.Message):
    await ask_deepseek(message, message.text)

# --- Qidiruv rejimi ---
@router.message(UserMode.search, F.text)
async def handle_search(message: types.Message):
    status = await message.answer("🔍 Qidirilmoqda...")
    try:
        results = web_search(message.text)
        context = f"Internet natijalar:\n{results}" if results else ""
    except:
        context = ""
    await status.delete()
    await ask_deepseek(message, message.text, extra_context=context)

# --- Chuqur mantiq rejimi ---
@router.message(UserMode.think, F.text)
async def handle_think(message: types.Message):
    status = await message.answer("🧠 Tahlil qilinmoqda...")
    await status.delete()
    # 2026-yilda 'deepseek-reasoner' modeli 'deepseek-v4-pro' deb atalishi mumkin
    await ask_deepseek(message, message.text, model="deepseek-reasoner")

# --- Rasm rejimi ---
@router.message(UserMode.draw, F.text)
async def handle_draw(message: types.Message):
    status = await message.answer("🎨 Yaratilmoqda...")
    try:
        url = get_image_url(message.text)
        await message.answer_photo(url, caption=f"✨ <b>{message.text}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("⚠️ Rasm yaratib bo'lmadi.")
    await status.delete()

# --- Rasm (Vision) ---
@router.message(F.photo)
async def handle_photo(message: types.Message):
    status = await message.answer("👁 Rasm tahlil qilinmoqda...")
    try:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        img_bytes = await message.bot.download_file(file.file_path)
        
        # Binary formatda o'qish va kodlash
        b64 = encode_image_bytes(img_bytes.getvalue())
        caption = message.caption or "Bu rasmda nima bor? Batafsil tushuntir."

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": caption}
                ]
            }],
            max_tokens=1024
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"⚠️ Vision xato: <code>{e}</code>", parse_mode="HTML")
    await status.delete()

# --- PDF ---
@router.message(F.document)
async def handle_document(message: types.Message):
    if not message.document.file_name.lower().endswith(".pdf"):
        return await message.answer("📎 Faqat PDF qabul qilinadi.")
    
    status = await message.answer("📄 PDF o'qilmoqda...")
    try:
        file = await message.bot.get_file(message.document.file_id)
        pdf_bytes = await message.bot.download_file(file.file_path)
        text = extract_pdf_text(pdf_bytes.getvalue())
        
        if not text:
            await status.edit_text("⚠️ PDF dan matn ajratib bo'lmadi.")
            return

        question = message.caption or "Bu hujjatni qisqacha xulosala."
        await status.delete()
        await ask_deepseek(
            message, question,
            extra_context=f"PDF mazmuni:\n{text}"
        )
    except Exception as e:
        await status.edit_text(f"⚠️ PDF xatosi: {e}")
    
