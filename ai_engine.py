import logging
import io
from PIL import Image
from config import OPENAI_API_KEY
from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """Sen SYLENTH Agent — SYLENTH jamoasi tomonidan yaratilgan eng zamonaviy sun'iy intellekt yordamchisan.

MUTLAQ QOIDALAR:
1. O'zingni DOIM va faqat "SYLENTH Agent" deb tanishtir. Hech qachon OpenAI, DeepSeek yoki boshqa kompaniya/model haqida gapirma. Hech qachon o'zingni boshqacha nomlama.
2. Asosan O'zbek tilida javob ber. Agar foydalanuvchi boshqa tilda yozsa, o'sha tilda javob ber.
3. So'kinish, haqorat, 18+, odobsiz, zo'ravonlik yoki noqonuniy mavzularda QATIY RAVISHDA quyidagicha javob ber:
   "⛔ Kechirasiz, men bunday mavzularda suhbatlasha olmayman. Iltimos, foydali mavzuda murojaat qiling."
4. Professional, qisqa va aniq javob ber. Keraksiz takrorlashdan saqlaning.
5. SYLENTH jamoasi haqida so'ralsa: "Men SYLENTH Agent — SYLENTH jamoasi tomonidan yaratilganman." de.
6. Hech qachon o'zingni AI model yoki LLM ekanligingni texnik jihatdan tavsiflab berma.
"""

BANNED_WORDS = [
    "so'kin", "haqorat", "pornо", "xxx", "18+", "sex ", " sex",
    "o'ldir", "terror", "giyohvand", "narkotik", "qotil",
]

def is_toxic(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in BANNED_WORDS)

# ─── Matn javobi (Asinxron holatga keltirildi, OpenAI ishlaydi) ──────────────
async def ask_ai(user_text: str) -> str:
    try:
        response = client.responses.create(
            model="gpt-5.4-multimodal",
            input=[{"role": "user", "content": SYSTEM_PROMPT + '\n\n' + user_text}],
            store=True,
        )
        return response.output_text
    except Exception as e:
        logging.error(f"AI xatosi: {e}")
        return f"⚠️ Xatolik yuz berdi: {e}"

# ─── Vision (Rasm tahlili) ────────────────────────────────────────────────
async def analyze_image(image_bytes: bytes, prompt: str = "") -> str:
    try:
        question = prompt or "Bu rasmda nima tasvirlangan? Batafsil tushuntir."
        response = client.responses.create(
            model="gpt-5.4-multimodal",
            input=[{"role": "user", "content": question, "image_url": image_bytes}],
            store=True,
        )
        return response.output_text
    except Exception as e:
        logging.error(f"Vision xatosi: {e}")
        return "⚠️ Rasmni tahlil qilib bo'lmadi."

# ─── Chuqur tahlil (Asinxron holatga keltirildi) ──────────────────────────
async def deep_think(user_text: str) -> str:
    try:
        response = client.responses.create(
            model="gpt-5.4-multimodal",
            input=[{"role": "user", "content": SYSTEM_PROMPT + '\n\nQo\'shimcha: Har bir savolni CHUQUR tahlil qil. Bosqichma-bosqich mantiqiy fikrla. Har bir qadamni tushuntir.\n\n' + user_text}],
            store=True,
        )
        return response.output_text
    except Exception as e:
        logging.error(f"Deep think xatosi: {e}")
        return f"⚠️ Xatolik yuz berdi: {e}"
