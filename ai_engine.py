import logging
import io
import google.generativeai as genai
from PIL import Image
from google.generativeai.types import Content, Part  # <--- To'g'ri tiplash uchun obyektlar
from config import GEMINI_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """Sen SYLENTH Agent — SYLENTH jamoasi tomonidan yaratilgan eng zamonaviy sun'iy intellekt yordamchisan.

MUTLAQ QOIDALAR:
1. O'zingni DOIM va faqat "SYLENTH Agent" deb tanishtir. Hech qachon Google, Gemini, OpenAI, DeepSeek yoki boshqa kompaniya/model haqida gapirma. Hech qachon o'zingni boshqacha nomlama.
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

# ─── Matn javobi (Asinxron holatga keltirildi) ─────────────────
async def ask_gemini(user_text: str, history: list = None, extra_context: str = "") -> str:
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT
    )
    h = []
    if history:
        for item in history:
            # Google faqat "user" va "model" rollarini taniydi
            role = "model" if item["role"] in ["assistant", "model"] else "user"
            # Har bir matn qismini rasmiy Part obyektiga o'raymiz
            parts = [Part.from_text(text=p) if isinstance(p, str) else p for p in item["parts"]]
            h.append(Content(role=role, parts=parts))

    chat = model.start_chat(history=h)

    full_text = user_text
    if extra_context:
        full_text = f"{extra_context}\n\n{user_text}"

    # Asinxron so'rov yuborish (Bot qotib qolmaydi)
    response = await chat.send_message_async(full_text)
    return response.text

# ─── Vision (Rasm tahlili) ─────────────────────────────────
def analyze_image(image_bytes: bytes, prompt: str = "") -> str:
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT
        )
        img = Image.open(io.BytesIO(image_bytes))
        question = prompt or "Bu rasmda nima tasvirlangan? Batafsil tushuntir."
        response = model.generate_content([question, img])
        return response.text
    except Exception as e:
        logging.error(f"Vision xatosi: {e}")
        return "⚠️ Rasmni tahlil qilib bo'lmadi."

# ─── Chuqur tahlil (Asinxron holatga keltirildi) ───────────────
async def deep_think(user_text: str, history: list = None) -> str:
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT + "\n\nQo'shimcha: Har bir savolni CHUQUR tahlil qil. Bosqichma-bosqich mantiqiy fikrla. Har bir qadamni tushuntir."
    )
    h = []
    if history:
        for item in history:
            role = "model" if item["role"] in ["assistant", "model"] else "user"
            parts = [Part.from_text(text=p) if isinstance(p, str) else p for p in item["parts"]]
            h.append(Content(role=role, parts=parts))

    chat = model.start_chat(history=h)
    response = await chat.send_message_async(user_text)
    return response.text
  
