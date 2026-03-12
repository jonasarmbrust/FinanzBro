"""Tests für den Telegram Service."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio


@pytest.fixture
def mock_settings():
    """Mock settings with Telegram config."""
    with patch("services.telegram.settings") as mock:
        mock.TELEGRAM_BOT_TOKEN = "test_token_123"
        mock.TELEGRAM_CHAT_ID = "12345678"
        yield mock


class TestSplitMessage:
    """Tests für die Nachrichten-Splitting-Logik."""

    def test_short_message_no_split(self):
        from services.telegram import _split_message
        result = _split_message("Hello World")
        assert result == ["Hello World"]

    def test_long_message_splits(self):
        from services.telegram import _split_message
        # Erstelle eine Nachricht die über 4096 Zeichen lang ist
        long_text = "\n".join([f"Line {i}: " + "x" * 80 for i in range(60)])
        assert len(long_text) > 4096
        result = _split_message(long_text)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 4096

    def test_empty_message(self):
        from services.telegram import _split_message
        result = _split_message("")
        assert result == [""]

    def test_exact_limit(self):
        from services.telegram import _split_message
        text = "x" * 4096
        result = _split_message(text)
        assert len(result) == 1


class TestSendMessage:
    """Tests für die Telegram send_message Funktion."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_settings):
        from services.telegram import send_message

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("services.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await send_message("Test Nachricht 🚀")

            assert result is True
            mock_client.post.assert_called_once()

            # Verify payload
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["chat_id"] == "12345678"
            assert payload["text"] == "Test Nachricht 🚀"
            assert payload["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        from services.telegram import send_message

        with patch("services.telegram.settings") as mock:
            mock.TELEGRAM_BOT_TOKEN = ""
            mock.TELEGRAM_CHAT_ID = ""
            result = await send_message("Test")
            assert result is False

    @pytest.mark.asyncio
    async def test_send_report(self, mock_settings):
        from services.telegram import send_report

        with patch("services.telegram.send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await send_report(
                "📊 Test Report",
                [
                    ("💰 Portfolio", "Wert: 50.000 EUR"),
                    ("🏆 Top", "AAPL: 80/100"),
                ],
            )

            assert result is True
            mock_send.assert_called_once()
            sent_text = mock_send.call_args[0][0]
            assert "Test Report" in sent_text
            assert "Portfolio" in sent_text
            assert "AAPL" in sent_text
