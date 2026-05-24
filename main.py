import asyncio import logging import os

Logging sozlamalari

logging.basicConfig( level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s" )

from aiogram import Bot, Dispatcher, types, F from aiogram.fsm.storage.memory import MemoryStorage from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, ADMIN_ID, DOWNLOADS_DIR, OPENAI_API_KEY from database import init_db, get_user from keyboards import main_menu from states import UserMode from middlewares.anti_flood import AntiFloodMiddleware from middlewares.access import AccessMiddleware

from handlers import commands, messages, media, ceo, group

bot = Bot(token=BOT_TOKEN) dp  = Dispatcher(storage=MemoryStorage())

Middleware'larni ro'yxatdan o'tkazish

dp.message.middleware(AntiFloodMiddleware()) dp.message.middleware(AccessMiddleware())

Routerlar

dp.include_router(commands.router) dp.include_router(ceo.router) dp.include_router(group.router) dp.include_router(media.router) dp.include_router(messages.router)

@dp.callback_query(F.data.startswith("mode_")) async def on_mode_select(callback: types.CallbackQuery, state: FSMContext): mode = callback.data.split("_")[1] config_modes = { "draw":   (UserMode.draw,   "🎨 <b>Rasm rejimi</b> — tavsif yozing\nMisol: <i>kiberpank shahar, neon chiroqlar</i>"), "search": (UserMode.search, "🔍 <b>Qidiruv rejimi</b> — savolingizni yozing"), "think":  (UserMode.think,  "🧠 <b>Chuqur tahlil</b> — murakkab savol yuboring"), "dl":     (UserMode.dl,     "📥 <b>Media rejimi</b> — video link yoki <code>/music qo'shiq</code>"), "chat":   (UserMode.chat,   "💬 <b>Suhbat rejimi</b> — istalganini yozing"), } if mode not in config_modes: return await callback.answer("Noma'lum rejim", show_alert=True) new_state, text = config_modes[mode] await state.set_state(new_state) await callback.message.edit_text(text + "\n\n🔙 /start — menyuga qaytish", parse_mode="HTML") await callback.answer("✅ Rejim o'rnatildi")

@dp.callback_query(F.data == "my_id") async def cb_my_id(callback: types.CallbackQuery): user = get_user(callback.from_user.id) if user: await callback.answer(f"🆔 SYLENTH ID: {user['sylenth_id']}\n💬 Xabarlar: {user['msg_count']}", show_alert=True)

@dp.callback_query(F.data == "help") async def cb_help(callback: types.CallbackQuery): await callback.message.edit_text( "📖 <b>SYLENTH Agent — Imkoniyatlar:</b>\n\n" "🎨 Rasm yaratish (Flux.1)\n🔍 Internet qidiruv\n" "🧠 Chuqur tahlil\n📥 Video/Musiqa yuklash\n" "👁 Rasm tahlil (Vision)\n📄 PDF o'qish\n\n" "/start /help /clear /id /draw /music", parse_mode="HTML", reply_markup=main_menu() )

@dp.callback_query(F.data == "cancel") async def cb_cancel(callback: types.CallbackQuery, state: FSMContext): await state.set_state(UserMode.chat) await callback.message.edit_text("❌ Bekor qilindi.", reply_markup=main_menu())

async def on_startup(): init_db() os.makedirs(DOWNLOADS_DIR, exist_ok=True)

description_text = (
    "🤖 SYLENTH Agent — sun'iy intellekt asosida ishlaydigan ko'p funksiyali universal yordamchi!\n\n"
    "Bu yerda siz:\n"
    "🧠 Har qanday savolga aqlli javob olishingiz (OpenAI AI);\n"
    "🎨 Tasavvuringizdagi rasmlarni chizdirishingiz (Flux.1);\n"
    "🔍 Internetdan real vaqtda ma'lumot qidirishingiz;\n"
    "📥 TikTok, Instagram, YouTube'dan video va musiqalar yuklashingiz;\n"
    "📄 PDF kitoblar va rasmlarni tahlil qilishingiz mumkin.\n\n"
    "Suhbatni boshlash uchun quyidagi 'Start' tugmasini bosing! 👇"
)
try:
    await bot.set_my_description(description_text)
    await bot.set_my_description(description_text, language_code="uz")
    await bot.set_my_description(description_text, language_code="ru")
except Exception as e:
    logging.warning(f"Description o'rnatishda xatolik: {e}")

me = await bot.get_me()
logging.info(f"🚀 SYLENTH Agent ishga tushdi! @{me.username}")

if ADMIN_ID:
    try:
        await bot.send_message(
            ADMIN_ID, 
            "🟢 <b>SYLENTH Agent online!</b>\n\nBot muvaffaqiyatli ishga tushdi va xizmatga tayyor.", 
            parse_mode="HTML"
        )
    except Exception:
        pass

async def main(): dp.startup.register(on_startup) await bot.delete_webhook(drop_pending_updates=True) await dp.start_polling(bot, allowed_updates=[ "message", "callback_query", "inline_query", "my_chat_member" ])

if name == "main": try: asyncio.run(main()) except (KeyboardInterrupt, SystemExit): logging.info("Bot to'xtatildi.")
