"""
Anti-flood middleware.
Limits users to 1 message per second to prevent spam/abuse.
"""

import time
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Minimum interval between messages (seconds)
THROTTLE_INTERVAL = 1.0

# Warning message for throttled users
THROTTLE_WARNING = "⚠️ Iltimos, sekinroq yozing. Har 1 soniyada 1 xabar yuboring."


class ThrottleMiddleware(BaseMiddleware):
    """
    Simple anti-flood middleware.
    Tracks last message time per user and skips messages that come too fast.
    """

    def __init__(self, interval: float = THROTTLE_INTERVAL) -> None:
        """
        Initialize throttle middleware.

        Args:
            interval: Minimum seconds between messages per user
        """
        self.interval = interval
        self._user_last_time: Dict[int, float] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        """Process incoming message and apply throttle."""
        user = event.from_user
        if not user:
            return await handler(event, data)

        user_id = user.id
        current_time = time.time()

        # Check last message time
        last_time = self._user_last_time.get(user_id, 0)
        time_diff = current_time - last_time

        if time_diff < self.interval:
            # Too fast - skip this message with a warning
            logger.debug(f"Throttled user {user_id} (interval: {time_diff:.2f}s)")
            try:
                await event.answer(THROTTLE_WARNING)
            except Exception:
                pass
            return None

        # Update last message time
        self._user_last_time[user_id] = current_time

        # Process the message normally
        return await handler(event, data)
