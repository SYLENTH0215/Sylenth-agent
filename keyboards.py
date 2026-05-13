from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎨 Rasm yaratish", callback_data="mode_draw"),
        types.InlineKeyboardButton(text="🔍 Qidirish",      callback_data="mode_search")
    )
    builder.row(
        types.InlineKeyboardButton(text="🧠 Chuqur mantiq", callback_data="mode_think"),
        types.InlineKeyboardButton(text="💬 Suhbat",        callback_data="mode_chat")
    )
    return builder.as_markup()
