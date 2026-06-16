"""
Clean import and boot verification.

Feature: project-hardening
Covers Requirements 14.1, 14.2 (Property 17) and log hygiene 12.1/12.2 (Property 18).

Each first-party module is imported with the required env vars present (set in
conftest before collection). Modules that depend on third-party packages are
skipped gracefully when those packages are not installed - that is an
environment limitation, not a first-party code defect.
"""

import asyncio
import importlib
import logging
from pathlib import Path

import pytest

# (module, [third-party deps required to import it])
FIRST_PARTY_MODULES = [
    ("config", []),
    ("bot.safety", []),
    ("bot.file_analyzer", []),
    ("handlers.utils", ["aiogram"]),
    ("middlewares.throttle", ["aiogram"]),
    ("database", ["aiosqlite"]),
    ("bot.search", ["ddgs"]),
    ("bot.downloader", ["yt_dlp"]),
    ("bot.ai_engine", ["google.generativeai", "aiosqlite"]),
    ("handlers.commands", ["aiogram", "aiosqlite"]),
    ("handlers.group", ["aiogram", "google.generativeai", "yt_dlp", "aiosqlite"]),
    ("handlers.private", ["aiogram", "google.generativeai", "yt_dlp", "aiosqlite"]),
    ("main", ["aiogram", "google.generativeai", "yt_dlp", "aiosqlite"]),
]


# --- Property 17: All first-party modules import cleanly ------------------
# Validates: Requirements 14.1


@pytest.mark.parametrize("module_name,deps", FIRST_PARTY_MODULES)
def test_first_party_module_imports_cleanly(module_name, deps):
    for dep in deps:
        pytest.importorskip(dep)
    module = importlib.import_module(module_name)
    assert module is not None


# --- Boot verification ----------------------------------------------------
# Validates: Requirements 14.2


def test_startup_logic_runs(tmp_path, monkeypatch):
    """init_db + downloads dir creation + stale cleanup complete without error."""
    pytest.importorskip("aiosqlite")
    pytest.importorskip("yt_dlp")

    import config
    import database
    from bot import downloader

    db_file = tmp_path / "boot.db"
    downloads_dir = tmp_path / "downloads"
    monkeypatch.setattr(config, "DB_PATH", str(db_file))
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    monkeypatch.setattr(downloader, "DOWNLOADS_DIR", str(downloads_dir))

    # Pre-seed a stale file to confirm cleanup removes it.
    downloads_dir.mkdir(parents=True, exist_ok=True)
    stale = downloads_dir / "stale.mp4"
    stale.write_text("x")

    asyncio.run(database.init_db())
    Path(downloads_dir).mkdir(parents=True, exist_ok=True)
    downloader.cleanup_stale_downloads()

    assert db_file.exists()
    assert not stale.exists()


# --- Property 18: Logs never contain credentials --------------------------
# Validates: Requirements 12.1, 12.2


def test_property_logs_exclude_credentials(caplog):
    """
    Property 18: error-path log records must not contain the bot token, the AI
    API key, or the admin id. We exercise the search error path with a mocked
    failure and assert the credentials never appear in emitted logs.
    """
    pytest.importorskip("ddgs")
    import config
    from bot import search
    from unittest.mock import patch

    secrets = [str(config.BOT_TOKEN), str(config.GEMINI_API_KEY), str(config.ADMIN_ID)]

    with caplog.at_level(logging.DEBUG):
        with patch.object(search, "DDGS", side_effect=RuntimeError("boom")):
            result = asyncio.run(search.search_web("test query"))

    # The error path returns the Uzbek error message, not the exception.
    assert "xatolik" in result.lower()
    for record in caplog.records:
        for secret in secrets:
            assert secret not in record.getMessage()
