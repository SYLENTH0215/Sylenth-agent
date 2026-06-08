import logging
from openai import OpenAI
from config import OPENAI_API_KEY

# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

SYSTEM_PROMPT = """Sen SYLENTH Agent — SYLENTH jamoasi tomonidan yaratilgan sun'iy intellekt yordamchisan.

MUTLAQ QOIDALAR:
1. Siz do'stona va xurmatli javob berish kerak
2. Har qanday tilda javob berish mumkin
3. Texnik savollar haqida to'liq ma'lumot ber
4. Tiq, odobsiz mavzularda javob berma
5. Agar bilamasan - ayriman deb ayt

QOBIL MAVZULAR: Ta'lim, Fan, Texnika, Sog'lik, Taklif

TAQIQ MAVZULAR: Zo'ravonlik, Jinsiy mazmun, Narkotika, Qotillik"""

BANNED_WORDS = [
    "so'kin", "haqorat", "pornо", "xxx", "18+", "sex", 
    "o'ldir", "terror", "giyohvand", "narkotik", "qotil",
    "abuse", "kill", "drug", "porn", "violence"
]

def is_toxic(text: str) -> bool:
    """Matni taqiq so'zlar uchun tekshirish"""
    if not text:
        return False
    text_lower = text.lower()
    return any(word in text_lower for word in BANNED_WORDS)

async def ask_ai(user_text: str, history: list = None, **kwargs) -> str:
    """AI dan javob so'rash (OpenAI GPT)"""
    if not client or not OPENAI_API_KEY:
        return "⚠️ AI xizmati hozirda mavjud emas. Xavfsizlik uchun API kalit o'rnatilmagan."
    
    try:
        messages_list = []
        
        # Tarixni qo'shish
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("parts", [msg.get("content", "")])[0] if isinstance(msg.get("parts"), list) else msg.get("content", "")
                messages_list.append({"role": role, "content": content})
        
        # Joriy xabar
        messages_list.append({"role": "user", "content": SYSTEM_PROMPT + "\n\n" + user_text})
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_list,
            temperature=0.7,
            max_tokens=2000,
            top_p=0.9
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"AI xatosi: {e}")
        return f"⚠️ Xatolik yuz berdi: {str(e)[:100]}"

async def analyze_image(image_bytes: bytes, prompt: str = "") -> str:
    """Rasmni tahlil qilish (Vision API)"""
    if not client or not OPENAI_API_KEY:
        return "⚠️ Rasm tahlili mavjud emas."
    
    try:
        import base64
        
        # Base64 ga o'girish
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        question = prompt or "Bu rasmda nima tasvirlangan? Tafsilotli javob ber."
        
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1024
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Rasm tahlili xatosi: {e}")
        return "⚠️ Rasmni tahlil qilib bo'lmadi."

async def deep_think(user_text: str, history: list = None, **kwargs) -> str:
    """Chuqur tahlil - ko'proq vaqt va token ishlatib fikr qilish"""
    if not client or not OPENAI_API_KEY:
        return "⚠️ Tahlil xizmati mavjud emas."
    
    try:
        enhanced_prompt = (
            "Siz bu savolga JUDA CHUQUR va BATAFSIL tahlil qilish kerak. "
            "Barcha aspektlarni ko'rib chiq, misollar ber, natijalarni summarize qil.\n\n" 
            + user_text
        )
        
        return await ask_ai(enhanced_prompt, history, **kwargs)
    except Exception as e:
        logging.error(f"Deep think xatosi: {e}")
        return f"⚠️ Xatolik yuz berdi: {str(e)[:100]}"

async def ask_gemini(user_text: str, history: list = None, **kwargs) -> str:
    """Gemini API (agar mavjud bo'lsa, lekin GPT ishlatamiz)"""
    # Groq yoki Google Gemini mavjud bo'lsa, shu yerdan o'rnatish mumkin
    # Hozir OpenAI ishlatamiz
    return await ask_ai(user_text, history, **kwargs)
