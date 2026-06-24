import os
import logging
from collections import deque
import asyncio
import httpx

from .web_search import web_search
from .channel_reader import get_channel_news
from .prompts import build_system_prompt

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

MODELS = [
    "z-ai/glm-5.1",
    "qwen/qwen3.5-397b-a17b",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "meta/llama-3.1-8b-instruct",
]

LOG_DIR = "group_logs"

DEFAULT_INSTRUCTION = build_system_prompt()


def _read_last_lines(folder, filename, n=200):
    file_path = os.path.join(folder, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return list(deque(f, maxlen=n))
    except FileNotFoundError:
        return []
    except Exception:
        return []


def _needs_search(message: str) -> bool:
    search_keywords = [
        "سرچ", "جستجو", "search", "پیدا کن",
        "قیمت", "آمار", "جدیدترین", "آخرین",
        "راهنما", "آموزش", "روش", "مراحل",
    ]
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in search_keywords)


def _needs_news(message: str) -> bool:
    news_keywords = [
        "اخبار", "خبر", "news", "چه خبر", "رویداد",
        "امروز", "دیروز", "این هفته", "اتفاق",
        "سیاسی", "اقتصادی", "ورزشی", "فناوری",
        "جهان", "ایران", "آمریکا", "اروپا",
    ]
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in news_keywords)


async def _call_model(client, model, payload, headers):
    payload["model"] = model
    try:
        resp = await client.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        )
        if resp.status_code == 429:
            return None, "rate_limited"
        if resp.status_code >= 500:
            return None, "server_error"
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"], None
    except httpx.TimeoutException:
        return None, "timeout"
    except httpx.ConnectError:
        return None, "connection"
    except httpx.HTTPStatusError as e:
        logging.error("NVIDIA API %s error: %s: %s", model, e.response.status_code, e.response.text)
        return None, "http_error"
    except Exception as e:
        logging.exception("NVIDIA API %s failed: %s", model, e)
        return None, "unknown"


async def get_response(group_id, message, system_prompt=None, username="کاربر"):
    if not NVIDIA_API_KEY:
        logging.error("NVIDIA_API_KEY not set in .env")
        return "کلید API تنظیم نشده."

    context_parts = []

    if _needs_news(message):
        logging.info("Channel news triggered for: %s", message)
        news = await get_channel_news(message)
        if news and "خطا" not in news:
            context_parts.append(f"## آخرین اخبار از کانال @VahidOnline:\n{news}")

    if _needs_search(message):
        logging.info("Web search triggered for: %s", message)
        search_result = await web_search(message)
        if search_result and "خطا" not in search_result:
            context_parts.append(f"## نتایج جستجوی وب:\n{search_result}")

    lines = _read_last_lines(LOG_DIR, f"group_{group_id}.txt")

    instruction = build_system_prompt(system_prompt) if system_prompt else DEFAULT_INSTRUCTION

    context_text = chr(10).join(lines) if lines else "(تاریخچه‌ای موجود نیست)"
    extra_context = "\n\n".join(context_parts)

    user_msg = (
        f"## تاریخچه چت گروه:\n{context_text}\n\n"
        f"{extra_context + chr(10) + chr(10) if extra_context else ''}"
        f"## پیام جدید:\n"
        f"کاربر «{username}» می‌گه: {message}\n\n"
        f"حالا جواب بده. Markdown خام و تمیز بنویس. HTML، JSON و MarkdownV2 escape ننویس. متن را طبیعی و بدون لحن تبلیغاتی نگه دار."
    )

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for model in MODELS:
            for attempt in range(3):
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                    "top_p": 0.9,
                }
                result, err = await _call_model(client, model, payload, headers)
                if result:
                    logging.info("Model %s responded successfully", model)
                    return result
                if err == "rate_limited":
                    logging.warning("Model %s rate limited, retry %d/3", model, attempt + 1)
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                if err in ("timeout", "connection", "server_error"):
                    logging.warning("Model %s %s, retry %d/3", model, err, attempt + 1)
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                break
            logging.warning("Model %s failed, trying next model", model)

    return "ایراد پیش اومد. چند دقیقه بعد دوباره امتحان کن."
