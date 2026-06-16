"""
Tests for the web search module (bot/search.py).

Feature: project-hardening
Covers Requirements 5.4, 5.5.

bot.search imports ddgs at module load; skips gracefully when ddgs is missing.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("ddgs")

from bot import search


def _mock_ddgs(results):
    """Build a context-manager mock whose .text() returns results."""
    instance = MagicMock()
    instance.text.return_value = iter(results)
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=instance)
    cm.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=cm)


def test_formats_results_numbered():
    results = [
        {"title": "First", "body": "Body one", "href": "http://a"},
        {"title": "Second", "body": "Body two", "href": "http://b"},
    ]
    with patch.object(search, "DDGS", _mock_ddgs(results)):
        output = asyncio.run(search.search_web("query"))
    assert "1." in output and "2." in output
    assert "First" in output and "Second" in output
    assert "http://a" in output and "http://b" in output


def test_empty_query():
    assert "qidiruv" in asyncio.run(search.search_web("")).lower()


def test_error_returns_uzbek_message():
    with patch.object(search, "DDGS", side_effect=RuntimeError("boom")):
        output = asyncio.run(search.search_web("query"))
    assert "xatolik" in output.lower()


# --- Property 3: Search result formatting is structure-preserving ---------
# Validates: Requirements 5.4


def test_property_formatting_structure_preserving():
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    result_strategy = st.fixed_dictionaries(
        {
            "title": st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
            "body": st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
            "href": st.from_regex(r"http://[a-z]{3,8}", fullmatch=True),
        }
    )

    @settings(max_examples=100)
    @given(results=st.lists(result_strategy, min_size=1, max_size=5))
    def run(results):
        with patch.object(search, "DDGS", _mock_ddgs(results)):
            output = asyncio.run(search.search_web("q"))
        # One numbered entry per result.
        for i, r in enumerate(results, 1):
            assert f"{i}." in output
            assert r["href"] in output
            # Title appears (body may be truncated, so only assert href+title).
            assert r["title"] in output

    run()


# --- Property 4: Search errors yield the fixed Uzbek message --------------
# Validates: Requirements 5.5


def test_property_errors_yield_uzbek_message():
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    exceptions = st.sampled_from(
        [RuntimeError("x"), ValueError("y"), TimeoutError("z"), OSError("w")]
    )

    @settings(max_examples=100)
    @given(exc=exceptions)
    def run(exc):
        with patch.object(search, "DDGS", side_effect=exc):
            output = asyncio.run(search.search_web("query"))
        assert "xatolik" in output.lower()

    run()
