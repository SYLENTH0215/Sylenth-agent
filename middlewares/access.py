from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject
from aiogram.exceptions import TelegramBadRequest
from config import REQUIRED_CHANNEL, ADMIN_ID
from database import is_banned, get_or_create_user
from keyboards import subscribe_btn

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not isinstance(event, Message):
            return await handler(event, data)
        user = event.from_user
        if not user or user.id == ADMIN_ID:
            return await handler(event, data)

        get_or_create_user(user.id, user.username or "", user.full_name or "")

        if is_banned(user.id):
            await event.answer("🚫 Siz botdan foydalanish huquqidan mahrum etildingiz.")
            return

        if REQUIRED_CHANNEL:
            bot: Bot = data["bot"]
            try:
                member = await bot.get_chat_member(REQUIRED_CHANNEL, user.id)
                if member.status in ("left", "kicked", "banned"):
                    await event.answer(
                        "📢 Botdan foydalanish uchun kanalga obuna bo'ling:",
                        reply_markup=subscribe_btn(REQUIRED_CHANNEL),
                        parse_mode="HTML"
                    )
                    return
            except TelegramBadRequest:
                pass

        return await handler(event, data)
