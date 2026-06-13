"""
Anti-flood middleware.
Limits users to 1 message per second to prevent spam/abuse.
Includes periodic eviction of stale entries and single-warning behavior.
"""

import time
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Minimum interval between messages (seconds)
THROTTLE_INTERVAL = 1.0

# Eviction threshold: remove entries older than this (seconds)
EVICTION_AGE = 60.0

# How often to run eviction (seconds)
EVICTION_INTERVAL = 30.0

# Warning message for throttled users
THROTTLE_WARNING = "\u26a0\ufe0f Iltimos, sekinroq yozing. Har 1 soniyada 1 xabar yuboring."


class ThrottleMiddleware(BaseMiddleware):
    """
    Simple anti-flood middleware.
    Tracks last message time per user and skips messages that come too fast.
    Warns only once per throttle burst, then silently drops subsequent messages.
    Periodically evicts stale entries to prevent unbounded memory growth.
    """

    def __init__(self, interval: float = THROTTLE_INTERVAL) -> None:
        """
        Initialize throttle middleware.

        Args:
            interval: Minimum seconds between messages per user
        """
        self.interval = interval
        self._user_last_time: Dict[int, float] = {}
        self._user_warned: Dict[int, bool] = {}
        self._last_eviction: float = time.time()
        super().__init__()

    def _evict_stale_entries(self, current_time: float) -> None:
        """Remove entries older than EVICTION_AGE to prevent unbounded growth."""
        if current_time - self._last_eviction < EVICTION_INTERVAL:
            return

        self._last_eviction = current_time
        stale_threshold = current_time - EVICTION_AGE

        stale_users = [
            uid for uid, last_t in self._user_last_time.items()
            if last_t < stale_threshold
        ]
        for uid in stale_users:
            del self._user_last_time[uid]
            self._user_warned.pop(uid, None)

        if stale_users:
            logger.debug(f"Evicted {len(stale_users)} stale throttle entries")

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

        # Periodically evict stale entries
        self._evict_stale_entries(current_time)

        # Check last message time
        last_time = self._user_last_time.get(user_id, 0)
        time_diff = current_time - last_time

        if time_diff < self.interval:
            # Too fast - warn once, then silently drop
            logger.debug(f"Throttled user {user_id} (interval: {time_diff:.2f}s)")
            if not self._user_warned.get(user_id, False):
                self._user_warned[user_id] = True
                try:
                    await event.answer(THROTTLE_WARNING)
                except Exception:
                    pass
            return None

        # Update last message time and reset warned flag
        self._user_last_time[user_id] = current_time
        self._user_warned[user_id] = False

        # Process the message normally
        return await handler(event, data)
