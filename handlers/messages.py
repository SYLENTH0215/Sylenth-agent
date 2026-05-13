import os
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from openai import OpenAI
from database import save_message, get_history
from utils import web_search, encode_image_bytes, extract_pdf_text, get_image_url
from states import UserMode

router = Router()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_KEY"),
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

    save_message(chat_id, user_id, "user", user_text)
    history = get_history(chat_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if extra_context:
        messages.append({"role": "system", "content": extra_context})
    messages += history

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048
        )
        reply = response.choices[0].message.content
        save_message(chat_id, user_id, "assistant", reply)
        await message.answer(reply, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ Xato: <code>{e}</code>", parse_mode="HTML")

# --- Oddiy matn ---
@router.message(UserMode.chat, F.text)
async def handle_chat(message: types.Message):
    await ask_deepseek(message, message.text)

# --- Qidiruv rejimi ---
@router.message(UserMode.search, F.text)
async def handle_search(message: types.Message):
    status = await message.answer("🔍 Qidirilmoqda...")
    results = web_search(message.text)
    context = f"Internet natijalar:\n{results}" if results else ""
    await status.delete()
    await ask_deepseek(message, message.text, extra_context=context)

# --- Chuqur mantiq rejimi ---
@router.message(UserMode.think, F.text)
async def handle_think(message: types.Message):
    status = await message.answer("🧠 Tahlil qilinmoqda...")
    await status.delete()
    await ask_deepseek(message, message.text, model="deepseek-reasoner")

# --- Rasm rejimi ---
@router.message(UserMode.draw, F.text)
async def handle_draw(message: types.Message):
    status = await message.answer("🎨 Yaratilmoqda...")
    url = get_image_url(message.text)
    try:
        await message.answer_photo(url, caption=f"✨ <b>{message.text}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("⚠️ Rasm yaratib bo'lmadi.")
    await status.delete()

# --- Rasm (Vision) ---
@router.message(F.photo)
async def handle_photo(message: types.Message):
    status = await message.answer("👁 Rasm tahlil qilinmoqda...")
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    img_bytes = await message.bot.download_file(file.file_path)
    b64 = encode_image_bytes(img_bytes.read())
    caption = message.caption or "Bu rasmda nima bor? Batafsil tushuntir."

    try:
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
    if not message.document.file_name.endswith(".pdf"):
        return await message.answer("📎 Faqat PDF qabul qilinadi.")
    status = await message.answer("📄 PDF o'qilmoqda...")
    file = await message.bot.get_file(message.document.file_id)
    pdf_bytes = await message.bot.download_file(file.file_path)
    text = extract_pdf_text(pdf_bytes.read())
    if not text:
        return await message.answer("⚠️ PDF dan matn ajratib bo'lmadi.")
    question = message.caption or "Bu hujjatni qisqacha xulosala."
    await status.delete()
    await ask_deepseek(
        message, question,
        extra_context=f"PDF mazmuni:\n{text}"
)
