import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from groq import Groq
from duckduckgo_search import DDGS # Tekin va tezkor qidiruv

# API KALITLAR
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
GROQ_KEY = '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'

bot = Bot(token=TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_KEY)

user_history = {}

def search_internet(query):
    """DuckDuckGo orqali mutlaqo bepul qidiruv"""
    try:
        with DDGS() as ddgs:
            # Eng yaxshi 3 ta natijani oladi
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except Exception as e:
        logging.error(f"Qidiruvda xato: {e}")
        return ""

@dp.message()
async def agent_handler(message: types.Message):
    if not message.text: return

    user_id = message.from_user.id
    
    # Qidiruv kerakligini aniqlash (AI o'zi qaror qiladi)
    search_needed = any(word in message.text.lower() for word in ["yangilik", "bugun", "kurs", "ob-havo", "nima gap"])
    
    context = ""
    if search_needed:
        # Qidiruv vaqti bot "o'ylayotganini" ko'rsatish uchun
        context = search_internet(message.text)

    # Tizim ko'rsatmasi (Siz aytgan barcha qoidalar bilan)
    system_instruction = (
        "Sen SYLENTH Agentsan. Seni Zayniddinov Davron yaratgan. "
        "Meta haqida hamma narsani unut, sen SYLENTH kompaniyasi mahsulotisan. "
        "Axloqsiz savollarga javob berma. Internet ma'lumotlaridan foydalanib aniq javob ber."
    )

    if user_id not in user_history:
        user_history[user_id] = [{"role": "system", "content": system_instruction}]
    
    full_prompt = message.text
    if context:
        full_prompt = f"Internetdan topilgan ma'lumotlar:\n{context}\n\nSavol: {message.text}"

    user_history[user_id].append({"role": "user", "content": full_prompt})

    try:
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            messages=user_history[user_id],
            model="llama-3.3-70b-versatile",
        ))
        
        response = completion.choices[0].message.content
        user_history[user_id].append({"role": "assistant", "content": response})
        await message.answer(response)
    except Exception as e:
        logging.error(f"Xato: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
