import asyncio
import logging
import os

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# ─── 🔑 BOTGA TEGISHLI MAXFIY MA'LUMOTLAR (.ENV O'RNIGA) ───────────────
BOT_TOKEN        = "8701673908:AAGk2e6J8X79AvVE2VuajywwiuvnK_GhqC8"
GEMINI_KEY       = "AIzaSyAjLWGKSt3s21SooD7jSVKU3394wUDyw_4"
ADMIN_ID         = 8103843122
REQUIRED_CHANNEL = ""  # Bo'sh qoldirildi (Majburiy obuna tekshirilmaydi)

# Ichki tizim sozlamalari
GEMINI_MODEL     = "gemini-2.0-flash-lite"
FLOOD_RATE       = 1.5   # soniya
BAN_THRESHOLD    = 5
MAX_FILE_MB      = 45   
DOWNLOADS_DIR    = "downloads"

# Boshqa handlerlar ichidagi 'from config import ...' kodlari muammosiz 
# ishlashi uchun ob'ektlarni virtual config moduli sifatida tizimga kiritamiz:
import sys
from types import ModuleType
cfg = ModuleType('config')
cfg.BOT_TOKEN = BOT_TOKEN
cfg.GEMINI_KEY = GEMINI_KEY
cfg.ADMIN_ID = ADMIN_ID
cfg.REQUIRED_CHANNEL = REQUIRED_CHANNEL
cfg.GEMINI_MODEL = GEMINI_MODEL
cfg.FLOOD_RATE = FLOOD_RATE
cfg.BAN_THRESHOLD = BAN_THRESHOLD
cfg.MAX_FILE_MB = MAX_FILE_MB
cfg.DOWNLOADS_DIR = DOWNLOADS_DIR
sys.modules['config'] = cfg
# ──────────────────────────────────────────────────────────────────────

from database import init_db
from keyboards import main_menu
from states import UserMode
from middlewares.anti_flood import AntiFloodMiddleware
from middlewares.access import AccessMiddleware
from handlers import commands, messages, media, ceo, group  # Media moduli ulandi

# Bot va Dispatcher obyektlari
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# Middleware'larni ulash
dp.message.middleware(AntiFloodMiddleware())
dp.message.middleware(AccessMiddleware())

# Routerlarni to'g'ri ketma-ketlikda ulash
dp.include_router(commands.router)
dp.include_router(ceo.router)
dp.include_router(group.router)
dp.include_router(media.router)     # Media yuklash va rasm chizish routeri muvaffaqiyatli joyida!
dp.include_router(messages.router)

# Rejim tanlash (Inline Keyboard Callbacks)
@dp.callback_query(F.data.startswith("mode_"))
async def on_mode_select(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]
    config_modes = {
        "draw":   (UserMode.draw,   "🎨 <b>Rasm rejimi</b> — tavsif yozing\nMisol: <i>kiberpank shahar, neon chiroqlar</i>"),
        "search": (UserMode.search, "🔍 <b>Qidiruv rejimi</b> — savolingizni yozing"),
        "think":  (UserMode.think,  "🧠 <b>Chuqur tahlil</b> — murakkab savol yuboring"),
        "dl":     (UserMode.dl,     "📥 <b>Media rejimi</b> — video link yoki <code>/music qo'shiq</code>"),
        "chat":   (UserMode.chat,   "💬 <b>Suhbat rejimi</b> — istalganini yozing"),
    }
    if mode not in config_modes:
        return await callback.answer("Noma'lum rejim", show_alert=True)
    new_state, text = config_modes[mode]
    await state.set_state(new_state)
    await callback.message.edit_text(text + "\n\n🔙 /start — menyuga qaytish", parse_mode="HTML")
    await callback.answer("✅ Rejim o'rnatildi")

@dp.callback_query(F.data == "my_id")
async def cb_my_id(callback: types.CallbackQuery):
    from database import get_user
    user = get_user(callback.from_user.id)
    if user:
        await callback.answer(f"🆔 SYLENTH ID: {user['sylenth_id']}\n💬 Xabarlar: {user['msg_count']}", show_alert=True)

@dp.callback_query(F.data == "help")
async def cb_help(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📖 <b>SYLENTH Agent — Imkoniyatlar:</b>\n\n"
        "🎨 Rasm yaratish (Flux.1)\n🔍 Internet qidiruv\n"
        "🧠 Chuqur tahlil\n📥 Video/Musiqa yuklash\n"
        "👁 Rasm tahlil (Vision)\n📄 PDF o'qish\n\n"
        "/start /help /clear /id /draw /music",
        parse_mode="HTML", reply_markup=main_menu()
    )

@dp.callback_query(F.data == "cancel")
async def cb_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserMode.chat)
    await callback.message.edit_text("❌ Bekor qilindi.", reply_markup=main_menu())

# Bot ishga tushgandagi jarayonlar
async def on_startup():
    init_db()
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    # 🤖 Botga birinchi marta kirganda (Start bosishdan oldin) ekranda chiqib turadigan tavsif matni
    description_text = (
        "🤖 SYLENTH Agent — sun'iy intellekt asosida ishlaydigan ko'p funksiyali universal yordamchi!\n\n"
        "Bu yerda siz:\n"
        "🧠 Har qanday savolga aqlli javob olishingiz (Gemini AI);\n"
        "🎨 Tasavvuringizdagi rasmlarni chizdirishingiz (Flux.1);\n"
        "🔍 Internetdan real vaqtda ma'lumot qidirishingiz;\n"
        "📥 TikTok, Instagram, YouTube'dan video va musiqalar yuklashingiz;\n"
        "📄 PDF kitoblar va rasmlarni tahlil qilishingiz mumkin.\n\n"
        "Suhbatni boshlash uchun quyidagi 'Start' tugmasini bosing! 👇"
    )
    try:
        await bot.set_my_description(description_text)
    except Exception as e:
        logging.warning(f"Description o'rnatishda xatolik: {e}")

    me = await bot.get_me()
    logging.info(f"🚀 SYLENTH Agent ishga tushdi! @{me.username}")
    
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID, 
                "🟢 <b>SYLENTH Agent online!</b>\n\nBot muvaffaqiyatli ishga tushdi. .env faylisiz xavfsiz ishlamoqda.", 
                parse_mode="HTML"
            )
        except Exception as e:
            logging.warning(f"Adminga start xabari yuborilmadi: {e}")

# Bot to'xtaganda adminga bildirishnoma yuborish
async def on_shutdown():
    logging.info("🔴 SYLENTH Agent o'chmoqda...")
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, "🔴 <b>SYLENTH Agent offline.</b>", parse_mode="HTML")
        except Exception:
            pass

# Main ishga tushirish funksiyasi
async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Kelib qolgan eski xabarlarni tozalab (drop_pending_updates) pollingni boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=[
        "message", "callback_query", "inline_query", "my_chat_member"
    ])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
        
