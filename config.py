"""
Bot configuration module.
All settings are defined directly here - no external .env file needed.
"""

# =============================================================================
# REQUIRED SETTINGS - Telegram Bot Token and OpenAI API Key
# =============================================================================

BOT_TOKEN: str = "8701673908:AAGk2e6J8X79AvVE2VuajywwiuvnK_GhqC8"
OPENAI_API_KEY: str = "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"
ADMIN_ID: int = 8103843122

# =============================================================================
# DATABASE SETTINGS
# =============================================================================

DB_PATH: str = "bot_database.db"

# =============================================================================
# OPENAI SETTINGS
# =============================================================================

OPENAI_MODEL: str = "gpt-4o-mini"
MAX_TOKENS: int = 2048
TEMPERATURE: float = 0.7

# =============================================================================
# CONVERSATION SETTINGS
# =============================================================================

HISTORY_LIMIT: int = 50
