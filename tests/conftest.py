"""
Shared pytest fixtures and configuration.

Critically, dummy values for the required environment variables are set
*before* any first-party module is imported, so importing ``config`` (and the
modules that import it) succeeds during test collection.
"""

import os

# --- Set required env vars BEFORE any first-party import -------------------
os.environ.setdefault("BOT_TOKEN", "test-bot-token")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ADMIN_ID", "123456789")

import sys
from pathlib import Path

import pytest

# Ensure the project root is importable when pytest is run from elsewhere.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """
    Point the database layer at a temporary SQLite file and initialize it.

    Skips automatically if aiosqlite is not installed in the environment.

    Returns the path to the temp database file.
    """
    aiosqlite = pytest.importorskip("aiosqlite")  # noqa: F841

    import config
    import database

    db_file = tmp_path / "test_bot.db"
    monkeypatch.setattr(config, "DB_PATH", str(db_file))
    monkeypatch.setattr(database, "DB_PATH", str(db_file))

    import asyncio

    asyncio.run(database.init_db())
    return str(db_file)
