import time
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from config import FLOOD_RATE, BAN_THRESHOLD, ADMIN_ID
from database import warn_user, ban_user

_last_msg: dict = {}
_flood_count: dict = {}

class AntiFloodMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not isinstance(event, Message):
            return await handler(event, data)
        user_id = event.from_user.id if event.from_user else None
        if not user_id or user_id == ADMIN_ID:
            return await handler(event, data)

        now  = time.time()
        diff = now - _last_msg.get(user_id, 0)

        if diff < FLOOD_RATE:
            _flood_count[user_id] = _flood_count.get(user_id, 0) + 1
            count = _flood_count[user_id]
            if count >= BAN_THRESHOLD:
                ban_user(user_id, "Anti-flood: avtomatik ban")
                await event.answer("🚫 Spam qoidasini buzganligi sababli bloklandingiz.")
                return
            elif count == 2:
                await event.answer(f"⚠️ Sekinroq yozing! ({BAN_THRESHOLD - count} ogohlantirish qoldi)")
            return

        _flood_count[user_id] = 0
        _last_msg[user_id] = now
        return await handler(event, data)

