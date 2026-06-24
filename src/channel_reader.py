import logging
import re
import httpx
from html import unescape
from datetime import datetime

CHANNEL_USERNAME = "VahidOnline"
CHANNEL_URL = f"https://t.me/s/{CHANNEL_USERNAME}"

_cache = {}
_cache_ttl = 300


async def read_channel_messages(limit: int = 10) -> str:
    """خواندن آخرین پیام‌های کانال تلگرام"""
    now = datetime.now().timestamp()
    if CHANNEL_USERNAME in _cache:
        cached_time, cached_data = _cache[CHANNEL_USERNAME]
        if now - cached_time < _cache_ttl:
            return cached_data

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                CHANNEL_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            resp.raise_for_status()
            html = resp.text

            messages = re.findall(
                r'<div class="tgme_widget_message_wrap[^"]*"[^>]*>.*?'
                r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>.*?'
                r'<time[^>]*datetime="([^"]*)"[^>]*>',
                html,
                re.DOTALL,
            )

            if not messages:
                messages = re.findall(
                    r'datetime="([^"]*)"[^>]*>.*?'
                    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
                    html,
                    re.DOTALL,
                )
                messages = [(m[1], m[0]) for m in messages]

            results = []
            for content, date_str in messages[:limit]:
                text = unescape(re.sub(r'<[^>]+>', ' ', content)).strip()
                text = re.sub(r'\s+', ' ', text)
                if text and len(text) > 10:
                    try:
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        date_str = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                    results.append(f"[{date_str}] {text}")

            if results:
                output = "\n\n".join(results)
                _cache[CHANNEL_USERNAME] = (now, output)
                return output

            return "پیامی از کانال خوانده نشد."

    except httpx.HTTPStatusError as e:
        logging.error("Channel fetch error: %s", e.response.status_code)
        return "خطا در خواندن کانال."
    except Exception as e:
        logging.exception("Channel reader failed: %s", e)
        return "خطا در خواندن کانال."


async def get_channel_news(query: str = "", limit: int = 5) -> str:
    """دریافت اخبار کانال با فیلتر جستجو"""
    all_messages = await read_channel_messages(limit=20)

    if not query or not all_messages.strip():
        lines = all_messages.split("\n\n")
        return "\n\n".join(lines[:limit])

    query_lower = query.lower()
    all_lines = all_messages.split("\n\n")
    matched = [
        line for line in all_lines
        if any(word in line.lower() for word in query_lower.split())
    ]

    if matched:
        return "\n\n".join(matched[:limit])

    return "\n\n".join(all_lines[:limit])
