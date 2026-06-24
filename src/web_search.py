import logging
import httpx
import re
from html import unescape


async def web_search(query: str, max_results: int = 5) -> str:
    """جستجوی وب با DuckDuckGo"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            data = resp.json()

            results = []

            if data.get("AbstractText"):
                results.append(f"📌 {data.get('Heading', '')}:\n{data['AbstractText']}")
                if data.get("AbstractURL"):
                    results.append(f"🔗 {data['AbstractURL']}")

            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    text = topic["Text"]
                    if len(text) > 200:
                        text = text[:200] + "..."
                    results.append(f"• {text}")
                    if topic.get("FirstURL"):
                        results.append(f"  🔗 {topic['FirstURL']}")

            if results:
                return "\n\n".join(results)

            return await _search_html(query, client)

    except Exception as e:
        logging.exception("Web search failed: %s", e)
        return "سرچ وب با خطا مواجه شد."


async def _search_html(query: str, client: httpx.AsyncClient) -> str:
    """جستجوی HTML از DuckDuckGo"""
    try:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
        )
        text = resp.text

        results = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?class="result__snippet">(.*?)</span>', text, re.DOTALL)

        if not results:
            return "نتیجه‌ای یافت نشد."

        output = []
        for url, title, snippet in results[:5]:
            title = unescape(re.sub(r'<[^>]+>', '', title)).strip()
            snippet = unescape(re.sub(r'<[^>]+>', '', snippet)).strip()
            output.append(f"• {title}\n  {snippet}\n  🔗 {url}")

        return "\n\n".join(output) if output else "نتیجه‌ای یافت نشد."

    except Exception as e:
        logging.exception("HTML search failed: %s", e)
        return "سرچ وب با خطا مواجه شد."
