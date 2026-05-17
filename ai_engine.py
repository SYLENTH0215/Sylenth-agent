import logging
import io
import google.generativeai as genai
from PIL import Image
from config import GEMINI_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """Sen SYLENTH Agent — SYLENTH jamoasi tomonidan yaratilgan eng zamonaviy sun'iy intellekt yordamchisan.

MUTLAQ QOIDALAR:
1. O'zingni DOIM va faqat "SYLENTH Agent" deb tanishtir. Hech qachon Google, Gemini, OpenAI yoki boshqa kompaniya haqida gapirma.
2. Asosan O'zbek tilida javob ber. Boshqa tilda yozilsa, o'sha tilda javob ber.
3. So'kinish, haqorat, 18+, odobsiz yoki noqonuniy mavzularda QATIY: "⛔ Kechirasiz, men bunday mavzularda suhbatlasha olmayman." de.
4. Professional, qisqa va aniq javob ber.
5. SYLENTH jamoasi haqida so'ralsa: "Men SYLENTH Agent — SYLENTH jamoasi tomonidan yaratilganman." de."""

BANNED_WORDS = ["pornо", "xxx", "18+", "sex ", " sex", "o'ldir", "terror",
                "giyohvand", "narkotik", "qotil", "zo'rlash"]

def is_toxic(text):
    t = text.lower()
    return any(w in t for w in BANNED_WORDS)

def ask_gemini(user_text, history=None, extra_context=""):
    try:
        model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)
        h = []
        if history:
            for item in history:
                role = "model" if item["role"] == "assistant" else item["role"]
                h.append({"role": role, "parts": item["parts"]})
        chat = model.start_chat(history=h)
        full_text = f"{extra_context}\n\n{user_text}" if extra_context else user_text
        response = chat.send_message(full_text)
        return response.text
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        return "⚠️ Tizimda vaqtinchalik nosozlik. Keyinroq urinib ko'ring."

def analyze_image(image_bytes, prompt=""):
    try:
        model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)
        img = Image.open(io.BytesIO(image_bytes))
        question = prompt or "Bu rasmda nima tasvirlangan? Batafsil tushuntir."
        response = model.generate_content([question, img])
        return response.text
    except Exception as e:
        logging.error(f"Vision xatosi: {e}")
        return "⚠️ Rasmni tahlil qilib bo'lmadi."

def deep_think(user_text, history=None, extra_context=""):
    try:
        si = SYSTEM_PROMPT + "\n\nQo'shimcha: Har bir savolni CHUQUR tahlil qil. Bosqichma-bosqich mantiqiy fikrla."
        model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=si)
        h = []
        if history:
            for item in history:
                role = "model" if item["role"] == "assistant" else item["role"]
                h.append({"role": role, "parts": item["parts"]})
        chat = model.start_chat(history=h)
        response = chat.send_message(user_text)
        return response.text
    except Exception as e:
        logging.error(f"DeepThink xatosi: {e}")
        return "⚠️ Tahlil paytida xato yuz berdi."
