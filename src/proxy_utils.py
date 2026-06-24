# src/proxy_utils.py

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

_DISABLE_PROXY_ENV_VARS = (
    "BOT_DISABLE_PROXY",
    "TELEGRAM_DISABLE_PROXY",
    "DISABLE_PROXY",
)

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUE_VALUES


def normalize_proxy_environment() -> None:
    """Normalize proxy environment variables for httpx/python-telegram-bot.

    httpx does not accept the generic ``socks://`` scheme. Many local proxy
    tools export values such as ``socks://127.0.0.1:10808``. For Telegram this
    should be ``socks5://127.0.0.1:10808``.

    Set BOT_DISABLE_PROXY=1 or TELEGRAM_DISABLE_PROXY=1 to ignore proxy
    environment variables completely.
    """

    if any(_is_true(os.getenv(name)) for name in _DISABLE_PROXY_ENV_VARS):
        for name in _PROXY_ENV_VARS:
            if name in os.environ:
                os.environ.pop(name, None)
        logger.info("Proxy environment disabled by config")
        return

    for name in _PROXY_ENV_VARS:
        value = os.getenv(name)
        if not value:
            continue

        stripped = value.strip()
        lower = stripped.lower()

        if lower.startswith("socks://"):
            fixed = "socks5://" + stripped[len("socks://") :]
            os.environ[name] = fixed
            logger.info("Normalized proxy env %s from socks:// to socks5://", name)
