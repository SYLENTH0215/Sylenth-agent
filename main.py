import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from groq import Groq

# API KALITLAR - O'zgartirilmadi
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
GROQ_KEY = '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'

# Loglarni yoqish
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Bot va AI obyektlarini yaratish
bot = Bot(token=TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_KEY)

@dp.message()
async def echo_handler(message: types.Message):
    if not message.text:
        return
        
    user_name = message.from_user.full_name
    
    try:
        # Groq sinxron kutubxona bo'lgani uchun uni alohida oqimda bajaramiz
        # Bu botni ko'p odam yozganda qotib qolishidan saqlaydi
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(None, lambda: client.chat.completions.create(

messages=[
    {
        "role": "system", 
        "content": f"Sen SYLENTH Agentsan. Sen SYLENTH jamoasi tomonidan yaratilgansan. Foydalanuvchi ({user_name}) bilan aqlli muloqot qil."
    },
                {"role": "user", "content": message.text}
                {"role": "system", "content": f"Sen SYLENTH Agentsan. Foydalanuvchi ({user_name}) qaysi tilda yozsa, sen ham o'sha tilda javob ber. Xushmuomala va aqlli bo'l, axloqiy qoidalar asosida javob ber, nojoʻya va qoʻpil gaplarga javob berma, har doim odob dpirasida muloqoqt qil"},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.3-70b-versatile",
        ))
        
        # Javobni yuborish
        await message.answer(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"Xato yuz berdi: {e}")

async def main():
    print("SYLENTH Agent ishga tushdi va xabarlarni kutmoqda...")
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
