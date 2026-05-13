import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI

# Sozlamalar
TOKEN = '8701673908:AAGJJHC-crHq0qJc8nPrZ6_7wsg4flzN7gM'
DEEPSEEK_KEY = 'sk-cc0d6273dd284087b41bc15ab32dfcd1'

bot = Bot(token=TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# 1. Rasm yaratish (/draw buyrug'i)
@dp.message(Command("draw"))
async def draw(msg: types.Message):
    prompt = msg.text.replace("/draw", "").strip()
    if not prompt: return await msg.answer("Rasm tavsifini yozing.")
    
    img_url = f"https://pollinations.ai/p/{prompt}?width=1024&height=1024&model=flux"
    await bot.send_photo(msg.chat.id, photo=img_url, caption="Tayyor! ✨")

# 2. Oddiy suhbat (DeepSeek-V3)
@dp.message(F.text)
async def chat(msg: types.Message):
    if msg.text.startswith("/"): return
    
    res = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Sen SYLENTH Agentsan. Oddiy va professional javob ber."},
            {"role": "user", "content": msg.text}
        ]
    )
    await msg.answer(res.choices[0].message.content)

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
