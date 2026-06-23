"""
Bot configuration module.

All credentials are loaded from the environment (process environment or an
optional ``.env`` file in the project root). No secrets are hardcoded here.

Required environment variables:
    BOT_TOKEN      - Telegram bot token
    GEMINI_API_KEY - Google Gemini API key
    ADMIN_ID       - Administrator Telegram id (integer)

If any required variable is missing/empty, loading fails fast with a clear
``RuntimeError`` that names the offending variable.
"""

import os
from pathlib import Path

# Optionally load a local .env file. python-dotenv is an optional dependency:
# if it is not installed, configuration is still read from the process
# environment. load_dotenv() does NOT override variables already present in the
# process environment, so process env wins over .env (precedence rule).
try:
    from dotenv import load_dotenv

    if Path(".env").exists():
        load_dotenv()
except ImportError:
    pass


def _require(name: str) -> str:
    """Return a required environment variable or raise naming the variable."""
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


# =============================================================================
# REQUIRED SETTINGS - loaded from the environment (no hardcoded secrets)
# =============================================================================

BOT_TOKEN: str = _require("BOT_TOKEN")
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")

try:
    ADMIN_ID: int = int(_require("ADMIN_ID"))
except ValueError as exc:
    raise RuntimeError(
        "Environment variable ADMIN_ID must be an integer"
    ) from exc

# =============================================================================
# DATABASE SETTINGS (non-secret)
# =============================================================================

DB_PATH: str = "bot_database.db"

# =============================================================================
# GEMINI SETTINGS (non-secret)
# =============================================================================

GEMINI_MODEL: str = "gemini-2.0-flash-lite"
MAX_TOKENS: int = 2048
TEMPERATURE: float = 0.7

# =============================================================================
# CONVERSATION SETTINGS (non-secret)
# =============================================================================

HISTORY_LIMIT: int = 50
