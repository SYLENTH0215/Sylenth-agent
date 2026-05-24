import logging
from openai import OpenAI

client = OpenAI(api_key="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")

SYSTEM_PROMPT = """Sen SYLENTH Agent — SYLENTH jamoasi tomonidan yaratilgan sun'iy intellekt yordamchisan.
MUTLAQ QOIDALAR: ..."""

BANNED_WORDS = ["so'kin","haqorat","pornо","xxx","18+","sex","o'ldir","terror","giyohvand","narkotik","qotil"]

def is_toxic(text: str) -> bool:
    return any(w in text.lower() for w in BANNED_WORDS)

async def ask_ai(user_text: str) -> str:
    try:
        response = client.responses.create(
            model="gpt-5.4-multimodal",
            input=[{"role": "user", "content": SYSTEM_PROMPT + "\n\n" + user_text}],
            store=True,
        )
        return response.output_text
    except Exception as e:
        logging.error(f"AI xatosi: {e}")
        return f"⚠️ Xatolik yuz berdi: {e}"

async def analyze_image(image_bytes: bytes, prompt: str = "") -> str:
    try:
        question = prompt or "Bu rasmda nima tasvirlangan?"
        response = client.responses.create(
            model="gpt-5.4-multimodal",
            input=[{"role": "user", "content": question, "image_url": image_bytes}],
            store=True,
        )
        return response.output_text
    except Exception as e:
        logging.error(f"Vision xatosi: {e}")
        return "⚠️ Rasmni tahlil qilib bo'lmadi."

async def deep_think(user_text: str) -> str:
    try:
        response = client.responses.create(
            model="gpt-5.4-multimodal",
            input=[{"role": "user", "content": SYSTEM_PROMPT + "\n\nQo'shimcha: Har bir savolni CHUQUR tahlil qil.\n" + user_text}],
            store=True,
        )
        return response.output_text
    except Exception as e:
        logging.error(f"Deep think xatosi: {e}")
        return f"⚠️ Xatolik yuz berdi: {e}"
