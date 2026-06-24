import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.prompts import RICH_MARKDOWN_SYSTEM_PROMPT, build_system_prompt
from src.telegram_sender import TelegramSender


@pytest.fixture
def sender(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:fake-token")
    return TelegramSender()


def test_plain_ai_output_gets_light_rich_formatting(sender):
    out = sender._normalize_markdown("سلام داداش، خوبم. تو چطوری؟")
    assert out.startswith("**")
    assert "تو چطوری؟" in out


def test_existing_markdown_is_not_rewritten(sender):
    markdown = "## عنوان\n\n- **مورد:** توضیح"
    assert sender._normalize_markdown(markdown) == markdown


def test_custom_prompt_is_appended_without_losing_rich_rules():
    prompt = build_system_prompt("با لحن خیلی کوتاه جواب بده.")
    assert RICH_MARKDOWN_SYSTEM_PROMPT in prompt
    assert "با لحن خیلی کوتاه جواب بده." in prompt
    assert "Do not use Telegram MarkdownV2 escaping" in prompt


@pytest.mark.asyncio
async def test_send_bot_message_uses_rich_before_fallback(sender):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"ok": true}'

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post.return_value = mock_response
        MockClient.return_value = instance

        ok = await sender.send_bot_message(chat_id=123, markdown="**سلام**")

    assert ok is True
    assert instance.post.call_args[0][0].endswith("/sendRichMessage")
    payload = instance.post.call_args[1]["json"]
    assert payload["rich_message"]["markdown"] == "**سلام**"
