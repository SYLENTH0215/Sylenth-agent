from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    b = InlineKeyboardBuilder()
    b.row(
        types.InlineKeyboardButton(text="🎨 Rasm yaratish", callback_data="mode_draw"),
        types.InlineKeyboardButton(text="🔍 Qidirish",      callback_data="mode_search"),
    )
    b.row(
        types.InlineKeyboardButton(text="🧠 Chuqur tahlil", callback_data="mode_think"),
        types.InlineKeyboardButton(text="📥 Media yuklash", callback_data="mode_dl"),
    )
    b.row(
        types.InlineKeyboardButton(text="💬 Suhbat",        callback_data="mode_chat"),
        types.InlineKeyboardButton(text="📊 Mening ID",     callback_data="my_id"),
    )
    b.row(types.InlineKeyboardButton(text="❓ Yordam",      callback_data="help"))
    return b.as_markup()

def ceo_panel():
    b = InlineKeyboardBuilder()
    b.row(
        types.InlineKeyboardButton(text="📊 Statistika",       callback_data="ceo_stats"),
        types.InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="ceo_users"),
    )
    b.row(
        types.InlineKeyboardButton(text="📢 Broadcast",        callback_data="ceo_broadcast"),
        types.InlineKeyboardButton(text="🚫 Ban qilish",       callback_data="ceo_ban"),
    )
    b.row(
        types.InlineKeyboardButton(text="✅ Unban",            callback_data="ceo_unban"),
        types.InlineKeyboardButton(text="🗑 DB tozalash",      callback_data="ceo_cleardb"),
    )
    b.row(types.InlineKeyboardButton(text="🔙 Orqaga",         callback_data="back_main"))
    return b.as_markup()

def subscribe_btn(channel):
    b = InlineKeyboardBuilder()
    b.row(types.InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{channel.lstrip('@')}"))
    b.row(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
    return b.as_markup()

def cancel_btn():
    b = InlineKeyboardBuilder()
    b.row(types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return b.as_markup()
