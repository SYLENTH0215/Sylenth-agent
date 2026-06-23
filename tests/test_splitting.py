"""
Tests for long-message splitting (handlers/utils.py).

Feature: project-hardening
Covers Requirements 13.3.

handlers.utils imports aiogram at module load, so these tests skip gracefully
when aiogram is not installed.
"""

import re

import pytest

pytest.importorskip("aiogram")

from handlers.utils import _split_long_message


def _strip_ws(s: str) -> str:
    return re.sub(r"\s+", "", s)


def test_short_message_single_chunk():
    text = "qisqa xabar"
    chunks = _split_long_message(text)
    assert chunks == [text]


def test_long_message_split_within_limit():
    text = "a" * 10000
    chunks = _split_long_message(text, max_length=4096)
    assert len(chunks) > 1
    assert all(len(c) <= 4096 for c in chunks)


def test_split_preserves_content():
    text = ("word " * 2000).strip()
    chunks = _split_long_message(text, max_length=100)
    assert _strip_ws("".join(chunks)) == _strip_ws(text)


# --- Property 15: Message splitting bounds chunks and preserves content ----
# Validates: Requirements 13.3


def test_property_splitting():
    """
    Property 15: every chunk is within the limit and concatenating the chunks
    reconstructs the original text (modulo whitespace stripped at boundaries).
    """
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=100)
    @given(
        text=st.text(max_size=5000),
        max_length=st.integers(min_value=10, max_value=200),
    )
    def run(text, max_length):
        chunks = _split_long_message(text, max_length=max_length)
        # Every chunk respects the limit.
        assert all(len(c) <= max_length for c in chunks)
        # Non-whitespace content is preserved in order.
        assert _strip_ws("".join(chunks)) == _strip_ws(text)

    run()
