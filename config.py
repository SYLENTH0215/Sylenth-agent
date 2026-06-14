"""
Bot configuration module.
All settings are defined directly here - no external .env file needed.
"""

# =============================================================================
# REQUIRED SETTINGS - Telegram Bot Token and Gemini API Key
# =============================================================================

BOT_TOKEN: str = "8701673908:AAGk2e6J8X79AvVE2VuajywwiuvnK_GhqC8"
GEMINI_API_KEY: str = "AIzaSyDl2wENBc9s4mJKsPhW3Mu6h3DAqtF-294"
ADMIN_ID: int = 8103843122

# =============================================================================
# DATABASE SETTINGS
# =============================================================================

DB_PATH: str = "bot_database.db"

# =============================================================================
# GEMINI SETTINGS
# =============================================================================

GEMINI_MODEL: str = "gemini-2.0-flash-lite"
MAX_TOKENS: int = 2048
TEMPERATURE: float = 0.7

# =============================================================================
# CONVERSATION SETTINGS
# =============================================================================

HISTORY_LIMIT: int = 50
