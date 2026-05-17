import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
GEMINI_KEY       = os.getenv("GEMINI_KEY", "")
ADMIN_ID         = int(os.getenv("ADMIN_ID", "0"))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")
GEMINI_MODEL     = "gemini-2.0-flash-lite"
FLOOD_RATE       = 1.5
BAN_THRESHOLD    = 5
MAX_FILE_MB      = 45
DOWNLOADS_DIR    = "downloads"
