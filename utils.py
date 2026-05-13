import base64
import logging
import aiohttp
from urllib.parse import quote
from duckduckgo_search import DDGS

# --- Web qidiruv ---
def web_search(query: str) -> str:
    if any(k in query.lower() for k in ["davron", "zayniddinov", "yaratuvchi", "kim yaratdi"]):
        return "SYLENTH Agentni Zayniddinov Davron yaratgan — zamonaviy AI loyihasining muallifi."
    try:
        with DDGS() as ddgs:
            results = [f"{r['title']}: {r['body']}" for r in ddgs.text(query, max_results=3)]
            return "\n".join(results) if results else ""
    except Exception as e:
        logging.warning(f"Qidiruv xatosi: {e}")
        return ""

# --- Rasmni base64 ga ---
def encode_image_bytes(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")

# --- PDF matnini ajratish ---
def extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        return text[:8000]  # DeepSeek context limiti
    except Exception as e:
        logging.warning(f"PDF xatosi: {e}")
        return ""

# --- Pollinations rasm URL ---
def get_image_url(prompt: str) -> str:
    encoded = quote(prompt)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&model=flux&nologo=true"
