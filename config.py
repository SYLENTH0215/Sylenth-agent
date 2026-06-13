"""
Bot configuration module.
Loads environment variables from .env file and validates required settings.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


def _get_required_env(key: str) -> str:
    """Get a required environment variable or exit with an error."""
    value = os.getenv(key)
    if not value:
        print(f"[CONFIG ERROR] {key} environment variable is not set!")
        print(f"Please set {key} in your .env file.")
        sys.exit(1)
    return value.strip()


# Required settings
BOT_TOKEN: str = _get_required_env("BOT_TOKEN")
OPENAI_API_KEY: str = _get_required_env("OPENAI_API_KEY")

# Admin ID (optional but recommended)
_admin_id_raw = os.getenv("ADMIN_ID", "0")
try:
    ADMIN_ID: int = int(_admin_id_raw.strip())
except ValueError:
    ADMIN_ID = 0

# Database path
DB_PATH: str = os.getenv("DB_PATH", "bot_database.db")

# OpenAI settings
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2048"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))

# Conversation history limit
HISTORY_LIMIT: int = int(os.getenv("HISTORY_LIMIT", "50"))
