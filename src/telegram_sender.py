# src/telegram_sender.py

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from src.proxy_utils import normalize_proxy_environment

logger = logging.getLogger(__name__)


class TelegramSender:
    """Centralized Telegram sending layer.

    Main project rule:
    - All bot/user-facing messages should go through send_bot_message/send_ai_response.
    - Main path is Telegram Bot API sendRichMessage.
    - sendMessage is only a plain-text fallback when Rich Messages fail.
    """

    RICH_MESSAGE_LIMIT_BYTES = 32768
    PLAIN_MESSAGE_LIMIT_CHARS = 4096

    _MARKDOWN_SIGNAL_RE = re.compile(
        r"(^#{1,6}\s|\*\*.+?\*\*|_.+?_|`[^`]+`|```|^\s*[-*+]\s+|^\s*\d+\.\s+|\|.+\||\$[^$]+\$|\$\$|\[[^\]]+\]\([^)]+\))",
        re.MULTILINE | re.DOTALL,
    )

    def __init__(self, bot_token: str | None = None) -> None:
        normalize_proxy_environment()

        self.bot_token = (
            bot_token
            or os.getenv("BOT_TOKEN")
            or os.getenv("TELEGRAM_BOT_TOKEN")
        )

        if not self.bot_token:
            raise RuntimeError(
                "Missing Telegram bot token. Set BOT_TOKEN or TELEGRAM_BOT_TOKEN in environment."
            )

        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_rich_message(
        self,
        chat_id: int | str,
        markdown: str,
        *,
        reply_to_message_id: int | None = None,
        is_rtl: bool = True,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        reply_markup: dict[str, Any] | None = None,
        skip_entity_detection: bool = False,
    ) -> bool:
        """Send a Telegram Rich Message using clean Markdown.

        Important:
        - Do not pass Telegram MarkdownV2 here.
        - Do not pre-escape Markdown.
        - The AI should generate clean Markdown.
        """

        cleaned = self._normalize_markdown(markdown)

        if not cleaned:
            cleaned = "**پاسخی برای ارسال وجود ندارد.**"

        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "rich_message": {
                "markdown": cleaned,
                "is_rtl": is_rtl,
                "skip_entity_detection": skip_entity_detection,
            },
        }

        if reply_to_message_id is not None:
            payload["reply_parameters"] = {
                "message_id": reply_to_message_id,
                "allow_sending_without_reply": True,
            }

        if disable_notification is not None:
            payload["disable_notification"] = disable_notification

        if protect_content is not None:
            payload["protect_content"] = protect_content

        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        logger.info("Sending Telegram Rich Message")
        logger.debug("Rich markdown payload preview: %s", cleaned[:1000])

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/sendRichMessage",
                    json=payload,
                )

            if response.status_code >= 400:
                logger.warning(
                    "sendRichMessage failed: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                return False

            return True

        except Exception:
            logger.exception("sendRichMessage request failed")
            return False

    async def send_plain_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        reply_to_message_id: int | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Safe fallback. Sends plain text without parse_mode."""

        text = (text or "").strip() or "پیام خالی بود."
        parts = self._split_plain_text(text)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for part in parts:
                    payload: dict[str, Any] = {
                        "chat_id": chat_id,
                        "text": part,
                    }

                    if reply_to_message_id is not None:
                        payload["reply_parameters"] = {
                            "message_id": reply_to_message_id,
                            "allow_sending_without_reply": True,
                        }

                    if reply_markup is not None:
                        payload["reply_markup"] = reply_markup

                    response = await client.post(
                        f"{self.api_base}/sendMessage",
                        json=payload,
                    )

                    if response.status_code >= 400:
                        logger.warning(
                            "sendMessage fallback failed: status=%s body=%s",
                            response.status_code,
                            response.text,
                        )
                        return False

            return True

        except Exception:
            logger.exception("sendMessage fallback request failed")
            return False

    async def send_bot_message(
        self,
        chat_id: int | str,
        markdown: str,
        *,
        reply_to_message_id: int | None = None,
        is_rtl: bool = True,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Main path for every visible bot message, fixed or AI-generated."""

        ok = await self.send_rich_message(
            chat_id=chat_id,
            markdown=markdown,
            reply_to_message_id=reply_to_message_id,
            is_rtl=is_rtl,
            reply_markup=reply_markup,
        )

        if ok:
            return True

        logger.warning("Falling back to plain text message")
        return await self.send_plain_message(
            chat_id=chat_id,
            text=self._markdown_to_readable_plain_text(markdown),
            reply_to_message_id=reply_to_message_id,
            reply_markup=reply_markup,
        )

    async def send_ai_response(
        self,
        chat_id: int | str,
        ai_answer: str,
        *,
        reply_to_message_id: int | None = None,
        is_rtl: bool = True,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Main path for every AI answer."""

        return await self.send_bot_message(
            chat_id=chat_id,
            markdown=ai_answer,
            reply_to_message_id=reply_to_message_id,
            is_rtl=is_rtl,
            reply_markup=reply_markup,
        )

    def _normalize_markdown(self, markdown: str) -> str:
        """Minimal cleanup only. Never convert to MarkdownV2."""

        text = (markdown or "").strip()

        # Remove accidental full-answer code fence if the model wrapped the whole response.
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()

        text = self._ensure_minimum_rich_markdown(text)

        # Rich Message limit is 32768 UTF-8 chars. Use bytes to stay conservative.
        if len(text.encode("utf-8")) > self.RICH_MESSAGE_LIMIT_BYTES:
            encoded = text.encode("utf-8")[:30000]
            text = encoded.decode("utf-8", errors="ignore").rstrip()
            text += "\n\n**ادامهٔ پاسخ به دلیل طول زیاد کوتاه شد.**"

        return text

    def _ensure_minimum_rich_markdown(self, text: str) -> str:
        """Make totally plain model output lightly rich.

        This is a guardrail for cases where the model ignores the prompt.
        It does not escape or rewrite real Markdown.
        """

        text = (text or "").strip()
        if not text:
            return text

        if self._MARKDOWN_SIGNAL_RE.search(text):
            return text

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return text

        if len(lines) == 1:
            one = lines[0]
            # Keep very short casual replies rich but not over-structured.
            if len(one) <= 180:
                # Split a casual follow-up question onto its own paragraph when possible.
                for marker in (" تو ", " شما ", " خودت "):
                    idx = one.find(marker)
                    if idx > 20 and "؟" in one[idx:]:
                        first = one[:idx].strip(" ،,")
                        rest = one[idx:].strip()
                        return f"**{first}**\n\n{rest}"
                return f"**{one}**"

            return f"**پاسخ:**\n\n{one}"

        first = lines[0]
        rest = "\n".join(lines[1:])
        return f"**{first}**\n\n{rest}"

    def _split_plain_text(self, text: str, limit: int = PLAIN_MESSAGE_LIMIT_CHARS) -> list[str]:
        """Plain sendMessage fallback has a 4096-character limit."""

        text = text or ""

        if len(text) <= limit:
            return [text]

        parts: list[str] = []
        current = ""

        for paragraph in text.split("\n\n"):
            candidate = paragraph if not current else current + "\n\n" + paragraph

            if len(candidate) <= limit:
                current = candidate
                continue

            if current:
                parts.append(current)
                current = ""

            while len(paragraph) > limit:
                split_at = paragraph.rfind("\n", 0, limit)
                if split_at < limit // 2:
                    split_at = paragraph.rfind(" ", 0, limit)
                if split_at < limit // 2:
                    split_at = limit

                parts.append(paragraph[:split_at].strip())
                paragraph = paragraph[split_at:].strip()

            if paragraph:
                current = paragraph

        if current:
            parts.append(current)

        return [part for part in parts if part]

    def _markdown_to_readable_plain_text(self, markdown: str) -> str:
        """Light plain-text fallback used only if Rich Message fails."""

        text = markdown or ""

        # Remove fenced code fence markers but keep code contents.
        text = re.sub(r"```[a-zA-Z0-9_-]*\n?", "", text)
        text = text.replace("```", "")

        replacements = {
            "**": "",
            "__": "",
            "~~": "",
            "==": "",
            "||": "",
            "`": "",
            "$$": "",
            "$": "",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Convert Markdown links to readable "label (url)".
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

        return text.strip()
