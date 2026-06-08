import os
from dotenv import load_dotenv

# .env faylni yuklash
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN muhim! .env faylida o'rnatish kerak")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")


# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PROJECT_NAME = "SylenthAgentBot"

# Groq
GROQ_KEY = os.getenv("GROQ_KEY", "")

# Bot sozlamalari
FLOOD_RATE = float(os.getenv("FLOOD_RATE", "1.5"))
BAN_THRESHOLD = int(os.getenv("BAN_THRESHOLD", "5"))
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "45"))
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")
