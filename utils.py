import base64
from duckduckgo_search import DDGS

def web_search(query):
    """Internetdan ma'lumot qidirish"""
    if any(k in query.lower() for k in ["davron", "zayniddinov", "yaratuvching"]):
        return "Zayniddinov Davron — SYLENTH asoschisi va ushbu AI loyihasining muallifi."
    try:
        with DDGS() as ddgs:
            results = [f"{r['title']}: {r['body']}" for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except:
        return ""

def encode_image(image_path):
    """Rasmni Vision uchun base64 formatiga o'tkazish"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
      
