"""
Web search module using DuckDuckGo.
Provides async web search functionality with formatted results.
"""

import asyncio
import logging
from typing import Optional

from ddgs import DDGS

logger = logging.getLogger(__name__)

# Finite timeout applied to the web-search network operation.
SEARCH_TIMEOUT_SECONDS = 20.0


async def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo and return formatted results.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted string with search results or error message
    """
    if not query or not query.strip():
        return "Iltimos, qidiruv so'rovini kiriting."

    try:

        def _search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            return results

        results = await asyncio.wait_for(
            asyncio.to_thread(_search), timeout=SEARCH_TIMEOUT_SECONDS
        )

        if not results:
            return f"'{query}' bo'yicha hech narsa topilmadi. Boshqa kalit so'zlar bilan urinib ko'ring."

        # Format results
        formatted_parts = [f"🔍 <b>Qidiruv natijalari:</b> «{query}»\n"]

        for i, result in enumerate(results, 1):
            title = result.get("title", "Sarlavhasiz")
            body = result.get("body", "Tavsif mavjud emas")
            href = result.get("href", "")

            # Truncate long body text
            if len(body) > 200:
                body = body[:200] + "..."

            formatted_parts.append(
                f"{i}. <b>{title}</b>\n"
                f"   {body}\n"
                f"   🔗 {href}\n"
            )

        return "\n".join(formatted_parts)

    except Exception as e:
        logger.error(f"Search error for query '{query}': {e}")
        return (
            "Qidiruv paytida xatolik yuz berdi. "
            "Iltimos, birozdan so'ng qayta urinib ko'ring. 🔄"
        )
