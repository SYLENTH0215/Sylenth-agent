"""
Tests for the file analyzer fallback (bot/file_analyzer.py).

Feature: project-hardening
Covers Requirements 8.2.

bot.file_analyzer imports only the standard library at module load (PyMuPDF /
python-docx / openpyxl are imported lazily inside functions), so these tests
run without third-party packages.
"""

import asyncio

import pytest

from bot.file_analyzer import analyze_file

UNSUPPORTED_MARKER = "tahlil qilish imkoni yo'q"


def test_undecodable_unknown_file_returns_unsupported(tmp_path):
    f = tmp_path / "mystery.xyz"
    f.write_bytes(b"\xff\xfe\x00\x01\x02binary\x80\x81")
    result = asyncio.run(analyze_file(str(f), "mystery.xyz"))
    assert UNSUPPORTED_MARKER in result


def test_decodable_unknown_file_returns_content(tmp_path):
    f = tmp_path / "notes.unknownext"
    f.write_text("hello world content")
    result = asyncio.run(analyze_file(str(f), "notes.unknownext"))
    assert "hello world content" in result


# --- Property 7: Unknown undecodable files return the unsupported message --
# Validates: Requirements 8.2


def test_property_undecodable_files_unsupported(tmp_path):
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=100, deadline=None)
    @given(
        payload=st.binary(min_size=0, max_size=64),
        ext=st.sampled_from([".xyz", ".bin", ".dat", ".unknown", ".qqq"]),
    )
    def run(payload, ext):
        # Prepend bytes that are never valid UTF-8 so decoding always fails.
        data = b"\xff\xfe" + payload
        f = tmp_path / f"file{ext}"
        f.write_bytes(data)
        result = asyncio.run(analyze_file(str(f), f"file{ext}"))
        assert UNSUPPORTED_MARKER in result

    run()
