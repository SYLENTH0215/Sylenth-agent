"""
Tests for the AI engine (bot/ai_engine.py).

Feature: project-hardening
Covers Requirements 3.2, 3.3, 3.4.

bot.ai_engine imports google.generativeai at module load; skips gracefully
when it (or aiosqlite, used by the database import) is missing.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("google.generativeai")
pytest.importorskip("aiosqlite")

from bot import ai_engine
from bot.ai_engine import ERROR_MESSAGE_UZ


# --- Unit: finite timeout is applied (3.2) --------------------------------


def test_gemini_call_times_out(monkeypatch):
    monkeypatch.setattr(ai_engine, "GEMINI_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(ai_engine, "GEMINI_MAX_RETRIES", 1)

    def slow_call():
        time.sleep(1.0)
        return "never"

    async def run():
        with pytest.raises(Exception):
            await ai_engine._gemini_call(slow_call)

    asyncio.run(run())


# --- Unit: retry count is bounded (3.4) -----------------------------------


def test_gemini_call_retry_bounded(monkeypatch):
    monkeypatch.setattr(ai_engine, "GEMINI_TIMEOUT_SECONDS", 5.0)
    monkeypatch.setattr(ai_engine, "GEMINI_MAX_RETRIES", 2)

    calls = {"n": 0}

    def failing_call():
        calls["n"] += 1
        raise RuntimeError("transient")

    async def run():
        with pytest.raises(RuntimeError):
            await ai_engine._gemini_call(failing_call)

    asyncio.run(run())
    # total attempts = retries + 1
    assert calls["n"] == 3


# --- Property 2: AI failures collapse to the error response ---------------
# Validates: Requirements 3.3, 3.4


def _run_get_ai_response_with_failure(exc_factory):
    """Drive get_ai_response with the Gemini chat raising the given exception."""
    fake_chat = MagicMock()
    fake_chat.send_message.side_effect = exc_factory()
    fake_model = MagicMock()
    fake_model.start_chat.return_value = fake_chat

    with patch.object(ai_engine, "is_prompt_injection", return_value=False), \
         patch.object(ai_engine, "is_safe", return_value=True), \
         patch.object(ai_engine, "get_conversation_history", new=AsyncMock(return_value=[])), \
         patch.object(ai_engine, "get_user_memories", new=AsyncMock(return_value={})), \
         patch.object(ai_engine, "save_message", new=AsyncMock()), \
         patch.object(ai_engine, "save_user_memory", new=AsyncMock()), \
         patch.object(ai_engine.genai, "GenerativeModel", return_value=fake_model), \
         patch.object(ai_engine, "GEMINI_TIMEOUT_SECONDS", 0.05), \
         patch.object(ai_engine, "GEMINI_MAX_RETRIES", 1):
        return asyncio.run(ai_engine.get_ai_response(1, "salom", "Bob"))


def test_transient_error_collapses_to_error_dict():
    result = _run_get_ai_response_with_failure(lambda: RuntimeError("boom"))
    assert result == {"type": "error", "content": ERROR_MESSAGE_UZ, "music_results": None}


def test_timeout_collapses_to_error_dict():
    def factory():
        def _slow(*args, **kwargs):
            time.sleep(1.0)
        return _slow

    # send_message is a slow function -> wait_for times out -> error dict.
    fake_chat = MagicMock()
    fake_chat.send_message = factory()
    fake_model = MagicMock()
    fake_model.start_chat.return_value = fake_chat

    with patch.object(ai_engine, "is_prompt_injection", return_value=False), \
         patch.object(ai_engine, "is_safe", return_value=True), \
         patch.object(ai_engine, "get_conversation_history", new=AsyncMock(return_value=[])), \
         patch.object(ai_engine, "get_user_memories", new=AsyncMock(return_value={})), \
         patch.object(ai_engine, "save_message", new=AsyncMock()), \
         patch.object(ai_engine, "save_user_memory", new=AsyncMock()), \
         patch.object(ai_engine.genai, "GenerativeModel", return_value=fake_model), \
         patch.object(ai_engine, "GEMINI_TIMEOUT_SECONDS", 0.05), \
         patch.object(ai_engine, "GEMINI_MAX_RETRIES", 1):
        result = asyncio.run(ai_engine.get_ai_response(1, "salom", "Bob"))

    assert result == {"type": "error", "content": ERROR_MESSAGE_UZ, "music_results": None}


def test_property_ai_failures_collapse():
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    exc_factories = st.sampled_from(
        [
            lambda: RuntimeError("x"),
            lambda: ValueError("y"),
            lambda: ConnectionError("z"),
            lambda: TimeoutError("t"),
        ]
    )

    @settings(max_examples=25, deadline=None)
    @given(factory=exc_factories)
    def run(factory):
        result = _run_get_ai_response_with_failure(factory)
        assert result == {
            "type": "error",
            "content": ERROR_MESSAGE_UZ,
            "music_results": None,
        }

    run()
