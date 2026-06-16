"""
Tests for the throttle middleware (middlewares/throttle.py).

Feature: project-hardening
Covers Requirements 6.3, 6.4, 6.5, 6.6.

Skips gracefully when aiogram is not installed.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("aiogram")

from aiogram.types import Message, CallbackQuery
from middlewares.throttle import ThrottleMiddleware, THROTTLE_WARNING


def _make_message(user_id=1):
    event = MagicMock(spec=Message)
    user = MagicMock()
    user.id = user_id
    event.from_user = user
    event.answer = AsyncMock()
    return event


def _make_callback(user_id=1):
    event = MagicMock(spec=CallbackQuery)
    user = MagicMock()
    user.id = user_id
    event.from_user = user
    event.answer = AsyncMock()
    return event


def test_message_passes_through_when_not_throttled():
    mw = ThrottleMiddleware()
    handler = AsyncMock(return_value="ok")
    event = _make_message()
    result = asyncio.run(mw(handler, event, {}))
    assert result == "ok"
    handler.assert_awaited_once()


def test_callback_accepted_without_type_error():
    """6.3: callback query events are accepted."""
    mw = ThrottleMiddleware()
    handler = AsyncMock(return_value="cb-ok")
    event = _make_callback()
    result = asyncio.run(mw(handler, event, {}))
    assert result == "cb-ok"
    handler.assert_awaited_once()


def test_no_user_pass_through():
    """6.6: events without from_user pass through unthrottled."""
    mw = ThrottleMiddleware()
    handler = AsyncMock(return_value="passed")
    event = MagicMock(spec=Message)
    event.from_user = None
    result = asyncio.run(mw(handler, event, {}))
    assert result == "passed"
    handler.assert_awaited_once()


def test_message_throttled_warns_once():
    """6.4: throttled message warns the user once per burst, then drops."""
    mw = ThrottleMiddleware()
    handler = AsyncMock(return_value="ok")

    async def scenario():
        event = _make_message(user_id=5)
        # First call goes through.
        await mw(handler, event, {})
        # Subsequent rapid calls are throttled.
        await mw(handler, event, {})
        await mw(handler, event, {})
        return event

    event = asyncio.run(scenario())
    # Warned exactly once across the burst.
    assert event.answer.await_count == 1
    event.answer.assert_awaited_with(THROTTLE_WARNING)


def test_callback_throttled_uses_answer_branch():
    """6.5: throttled callback is acknowledged via answer (not a reply)."""
    mw = ThrottleMiddleware()
    handler = AsyncMock(return_value="ok")

    async def scenario():
        event = _make_callback(user_id=7)
        await mw(handler, event, {})
        await mw(handler, event, {})
        return event

    event = asyncio.run(scenario())
    assert event.answer.await_count == 1
    # Called with the warning text and show_alert kwarg.
    args, kwargs = event.answer.await_args
    assert args[0] == THROTTLE_WARNING


# --- Property 5: Throttle handles both event types and missing users ------
# Validates: Requirements 6.3, 6.6


def test_property_dual_type_and_missing_user():
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=100)
    @given(kind=st.sampled_from(["message", "callback", "no_user"]))
    def run(kind):
        mw = ThrottleMiddleware()
        handler = AsyncMock(return_value="ok")
        if kind == "message":
            event = _make_message(user_id=1)
        elif kind == "callback":
            event = _make_callback(user_id=1)
        else:
            event = MagicMock(spec=Message)
            event.from_user = None
        # Must not raise a type error for any event kind.
        result = asyncio.run(mw(handler, event, {}))
        if kind == "no_user":
            assert result == "ok"
            handler.assert_awaited_once()

    run()
