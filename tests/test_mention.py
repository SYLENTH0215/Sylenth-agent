"""
Tests for case-insensitive group mention detection (handlers/group.py).

Feature: project-hardening
Covers Requirements 7.1, 7.2.

handlers.group transitively imports aiogram, google-generativeai, yt-dlp and
aiosqlite; these tests skip gracefully when any are missing.
"""

from types import SimpleNamespace

import pytest

pytest.importorskip("aiogram")
pytest.importorskip("google.generativeai")
pytest.importorskip("yt_dlp")
pytest.importorskip("aiosqlite")

from handlers.group import _is_bot_mentioned

BOT_USERNAME = "SylenthBot"


def _msg(text, entities=None):
    return SimpleNamespace(text=text, entities=entities)


@pytest.mark.parametrize(
    "text",
    [
        "@SylenthBot salom",
        "@sylenthbot salom",
        "@SYLENTHBOT salom",
        "@SylEnThBoT qalaysan",
        "hey @sylenthbot help",
    ],
)
def test_mention_in_text_case_insensitive(text):
    assert _is_bot_mentioned(_msg(text), BOT_USERNAME) is True


def test_no_mention():
    assert _is_bot_mentioned(_msg("oddiy xabar"), BOT_USERNAME) is False
    assert _is_bot_mentioned(_msg(""), BOT_USERNAME) is False
    assert _is_bot_mentioned(_msg(None), BOT_USERNAME) is False


def test_mention_entity_case_insensitive():
    text = "@SYLENTHBOT salom"
    entity = SimpleNamespace(type="mention", offset=0, length=len("@SYLENTHBOT"))
    assert _is_bot_mentioned(_msg(text, entities=[entity]), BOT_USERNAME) is True


# --- Property 6: Mention detection is case-insensitive --------------------
# Validates: Requirements 7.1, 7.2


def test_property_case_insensitive_mention():
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    def random_case(s, flags):
        return "".join(
            c.upper() if flag else c.lower() for c, flag in zip(s, flags)
        )

    @settings(max_examples=100)
    @given(flags=st.lists(st.booleans(), min_size=len(BOT_USERNAME), max_size=len(BOT_USERNAME)))
    def run_text(flags):
        variant = random_case(BOT_USERNAME, flags)
        text = f"salom @{variant}!"
        assert _is_bot_mentioned(_msg(text), BOT_USERNAME) is True

    run_text()

    @settings(max_examples=100)
    @given(flags=st.lists(st.booleans(), min_size=len(BOT_USERNAME), max_size=len(BOT_USERNAME)))
    def run_entity(flags):
        variant = random_case(BOT_USERNAME, flags)
        mention = f"@{variant}"
        text = f"{mention} hello"
        entity = SimpleNamespace(type="mention", offset=0, length=len(mention))
        assert _is_bot_mentioned(_msg(text, entities=[entity]), BOT_USERNAME) is True

    run_entity()
