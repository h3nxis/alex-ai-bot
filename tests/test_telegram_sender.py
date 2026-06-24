# tests/test_telegram_sender.py

import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.telegram_sender import TelegramSender


@pytest.fixture(autouse=True)
def _clear_proxy_env(monkeypatch):
    monkeypatch.delenv("ALL_PROXY", raising=False)
    monkeypatch.delenv("all_proxy", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)


@pytest.fixture
def sender():
    os.environ["BOT_TOKEN"] = "123:fake-token"
    return TelegramSender()


def _mock_httpx_client():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"ok": true}'
    mock_client.post.return_value = mock_response
    return mock_client, mock_response


class TestTelegramSenderInit:
    def test_init_with_token(self):
        os.environ["BOT_TOKEN"] = "123:fake-token"
        s = TelegramSender()
        assert s.bot_token == "123:fake-token"
        assert s.api_base == "https://api.telegram.org/bot123:fake-token"

    def test_init_with_explicit_token(self):
        s = TelegramSender(bot_token="999:explicit")
        assert s.bot_token == "999:explicit"

    def test_init_raises_without_token(self, monkeypatch):
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="Missing Telegram bot token"):
            TelegramSender()


class TestSendRichMessage:
    async def test_send_rich_message_success(self, sender):
        mock_client, mock_response = _mock_httpx_client()
        mock_response.status_code = 200
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.return_value = mock_response
            MockClient.return_value = instance

            result = await sender.send_rich_message(
                chat_id=12345,
                markdown="**Hello World**",
            )

            assert result is True
            call_args = instance.post.call_args
            payload = call_args[1]["json"]
            assert payload["chat_id"] == 12345
            assert payload["rich_message"]["markdown"] == "**Hello World**"
            assert payload["rich_message"]["is_rtl"] is True

    async def test_send_rich_message_with_reply(self, sender):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.return_value = mock_response
            MockClient.return_value = instance

            result = await sender.send_rich_message(
                chat_id=12345,
                markdown="Test",
                reply_to_message_id=99,
            )

            assert result is True
            payload = instance.post.call_args[1]["json"]
            assert payload["reply_parameters"]["message_id"] == 99
            assert payload["reply_parameters"]["allow_sending_without_reply"] is True

    async def test_send_rich_message_strips_code_fence(self, sender):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.return_value = mock_response
            MockClient.return_value = instance

            await sender.send_rich_message(
                chat_id=1,
                markdown="```markdown\n**Hello**\n```",
            )

            payload = instance.post.call_args[1]["json"]
            assert payload["rich_message"]["markdown"] == "**Hello**"

    async def test_send_rich_message_http_error_returns_false(self, sender):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"ok": false}'
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.return_value = mock_response
            MockClient.return_value = instance

            result = await sender.send_rich_message(
                chat_id=1,
                markdown="Test",
            )

            assert result is False

    async def test_send_rich_message_exception_returns_false(self, sender):
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.side_effect = Exception("Connection failed")
            MockClient.return_value = instance

            result = await sender.send_rich_message(
                chat_id=1,
                markdown="Test",
            )

            assert result is False


class TestSendPlainMessage:
    async def test_send_plain_single_part(self, sender):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.return_value = mock_response
            MockClient.return_value = instance

            result = await sender.send_plain_message(
                chat_id=123,
                text="Hello",
            )

            assert result is True
            payload = instance.post.call_args[1]["json"]
            assert payload["text"] == "Hello"
            assert "parse_mode" not in payload

    async def test_send_plain_long_text_splits(self, sender):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.return_value = mock_response
            MockClient.return_value = instance

            long_text = "A" * 8192
            result = await sender.send_plain_message(chat_id=1, text=long_text)

            assert result is True
            assert instance.post.call_count == 2

    async def test_send_plain_empty_text(self, sender):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post.return_value = mock_response
            MockClient.return_value = instance

            result = await sender.send_plain_message(chat_id=1, text="")

            assert result is True


class TestSendAiResponse:
    async def test_ai_response_uses_rich_first(self, sender):
        with patch.object(sender, "send_rich_message", new_callable=AsyncMock) as mock_rich:
            mock_rich.return_value = True

            result = await sender.send_ai_response(
                chat_id=1,
                ai_answer="**Bold** text",
                reply_to_message_id=10,
                is_rtl=False,
            )

            assert result is True
            mock_rich.assert_called_once_with(
                chat_id=1,
                markdown="**Bold** text",
                reply_to_message_id=10,
                is_rtl=False,
                reply_markup=None,
            )

    async def test_ai_response_falls_back_to_plain(self, sender):
        with patch.object(sender, "send_rich_message", new_callable=AsyncMock) as mock_rich:
            mock_rich.return_value = False
            with patch.object(sender, "send_plain_message", new_callable=AsyncMock) as mock_plain:
                mock_plain.return_value = True

                result = await sender.send_ai_response(
                    chat_id=1,
                    ai_answer="Test",
                )

                assert result is True
                mock_plain.assert_called_once()

    async def test_ai_response_all_fail_returns_false(self, sender):
        with patch.object(sender, "send_rich_message", new_callable=AsyncMock) as mock_rich:
            mock_rich.return_value = False
            with patch.object(sender, "send_plain_message", new_callable=AsyncMock) as mock_plain:
                mock_plain.return_value = False

                result = await sender.send_ai_response(
                    chat_id=1,
                    ai_answer="Test",
                )

                assert result is False


class TestNormalizeMarkdown:
    def test_strips_wrapping_code_fence(self, sender):
        result = sender._normalize_markdown("```markdown\n**Hello**\n```")
        assert result == "**Hello**"

    def test_preserves_inner_code_fences(self, sender):
        md = "## Code\n\n```python\nprint('hi')\n```"
        result = sender._normalize_markdown(md)
        assert result == md

    def test_empty_input(self, sender):
        result = sender._normalize_markdown("")
        assert result == ""

    def test_none_input(self, sender):
        result = sender._normalize_markdown(None)
        assert result == ""

    def test_long_text_truncates(self, sender):
        long_text = "A" * 40000
        result = sender._normalize_markdown(long_text)
        assert len(result) < len(long_text)
        assert "کوتاه شد" in result


class TestSplitPlainText:
    def test_short_text(self, sender):
        result = sender._split_plain_text("Hello")
        assert result == ["Hello"]

    def test_empty_text(self, sender):
        result = sender._split_plain_text("")
        assert result == [""]

    def test_splits_on_paragraphs(self, sender):
        text = ("Para 1\n\n" * 100).strip()
        result = sender._split_plain_text(text, limit=200)
        assert all(len(p) <= 200 for p in result)
        assert len(result) > 1

    def test_none_text(self, sender):
        result = sender._split_plain_text(None)
        assert result == [""]


class TestMarkdownToReadablePlainText:
    def test_removes_bold(self, sender):
        result = sender._markdown_to_readable_plain_text("**Hello**")
        assert result == "Hello"

    def test_removes_italic(self, sender):
        result = sender._markdown_to_readable_plain_text("__Hello__")
        assert result == "Hello"

    def test_removes_strikethrough(self, sender):
        result = sender._markdown_to_readable_plain_text("~~Hello~~")
        assert result == "Hello"

    def test_preserves_other_text(self, sender):
        result = sender._markdown_to_readable_plain_text("Hello World 123")
        assert result == "Hello World 123"

    def test_empty_input(self, sender):
        result = sender._markdown_to_readable_plain_text("")
        assert result == ""
