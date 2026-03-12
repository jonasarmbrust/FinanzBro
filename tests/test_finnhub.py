"""FinanzBro - Finnhub WebSocket Tests

Testet den FinnhubStreamer In-Memory-Cache, Subscribe/Unsubscribe-Logik
und REST-Fallback. Keine echte WebSocket-Verbindung nötig.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fetchers.finnhub_ws import FinnhubStreamer, fetch_finnhub_quote


# ==================== FinnhubStreamer Unit Tests ====================

class TestFinnhubStreamerCache:
    """Tests für den In-Memory-Preiscache."""

    def test_empty_cache_returns_none(self):
        streamer = FinnhubStreamer()
        assert streamer.get_price("AAPL") is None

    def test_update_and_get_price(self):
        streamer = FinnhubStreamer()
        streamer.update_price("AAPL", 175.50)
        assert streamer.get_price("AAPL") == 175.50

    def test_case_insensitive_get(self):
        streamer = FinnhubStreamer()
        streamer.update_price("aapl", 175.50)
        assert streamer.get_price("AAPL") == 175.50

    def test_get_all_prices(self):
        streamer = FinnhubStreamer()
        streamer.update_price("AAPL", 175.0)
        streamer.update_price("MSFT", 350.0)
        prices = streamer.get_all_prices()
        assert prices == {"AAPL": 175.0, "MSFT": 350.0}

    def test_get_all_prices_returns_copy(self):
        streamer = FinnhubStreamer()
        streamer.update_price("AAPL", 175.0)
        prices = streamer.get_all_prices()
        prices["AAPL"] = 999.0  # Modify copy
        assert streamer.get_price("AAPL") == 175.0  # Original unchanged

    def test_price_age(self):
        streamer = FinnhubStreamer()
        streamer.update_price("AAPL", 175.0)
        age = streamer.get_price_age("AAPL")
        assert age is not None
        assert age < 1.0  # Should be nearly instant

    def test_price_age_none_for_unknown(self):
        streamer = FinnhubStreamer()
        assert streamer.get_price_age("UNKNOWN") is None


class TestFinnhubStreamerSubscribe:
    """Tests für Subscribe/Unsubscribe-Logik."""

    def test_subscribe_us_tickers(self):
        streamer = FinnhubStreamer()
        streamer.subscribe(["AAPL", "MSFT", "GOOGL"])
        assert "AAPL" in streamer._subscribed
        assert "MSFT" in streamer._subscribed
        assert "GOOGL" in streamer._subscribed

    def test_subscribe_skips_de_tickers(self):
        """Deutsche Aktien (mit .DE) werden übersprungen."""
        streamer = FinnhubStreamer()
        streamer.subscribe(["SIE.DE", "BAYN.DE", "SAP.DE"])
        assert len(streamer._subscribed) == 0

    def test_subscribe_skips_isins(self):
        """ISIN-basierte Ticker werden übersprungen."""
        streamer = FinnhubStreamer()
        streamer.subscribe(["US0378331005", "DE000BAY0017"])
        assert len(streamer._subscribed) == 0

    def test_subscribe_skips_cash(self):
        """CASH-Position wird übersprungen."""
        streamer = FinnhubStreamer()
        streamer.subscribe(["CASH"])
        assert len(streamer._subscribed) == 0

    def test_subscribe_mixed(self):
        """Gemischte Ticker: nur US-Ticker abonniert."""
        streamer = FinnhubStreamer()
        streamer.subscribe(["AAPL", "SIE.DE", "MSFT", "CASH", "US0378331005"])
        assert streamer._subscribed == {"AAPL", "MSFT"}

    def test_subscribe_no_duplicates(self):
        """Doppelte Ticker werden nicht nochmal hinzugefügt."""
        streamer = FinnhubStreamer()
        streamer.subscribe(["AAPL"])
        streamer.subscribe(["AAPL", "MSFT"])
        assert len(streamer._subscribed) == 2

    def test_unsubscribe(self):
        streamer = FinnhubStreamer()
        streamer.subscribe(["AAPL", "MSFT"])
        streamer.update_price("AAPL", 175.0)
        streamer.unsubscribe(["AAPL"])
        assert "AAPL" not in streamer._subscribed
        assert streamer.get_price("AAPL") is None  # Cache cleared
        assert "MSFT" in streamer._subscribed  # Other unchanged


class TestFinnhubStreamerMessageProcessing:
    """Tests für WebSocket-Nachrichtenverarbeitung."""

    def test_process_trade_message(self):
        streamer = FinnhubStreamer()
        msg = '{"type":"trade","data":[{"s":"AAPL","p":175.50,"t":1234567890,"v":100}]}'
        streamer._process_message(msg)
        assert streamer.get_price("AAPL") == 175.50

    def test_process_multiple_trades(self):
        streamer = FinnhubStreamer()
        msg = '{"type":"trade","data":[{"s":"AAPL","p":175.50,"t":1234567890,"v":100},{"s":"MSFT","p":350.25,"t":1234567891,"v":50}]}'
        streamer._process_message(msg)
        assert streamer.get_price("AAPL") == 175.50
        assert streamer.get_price("MSFT") == 350.25

    def test_process_ping_message(self):
        """Ping-Messages sollen keine Fehler verursachen."""
        streamer = FinnhubStreamer()
        msg = '{"type":"ping"}'
        streamer._process_message(msg)  # Should not raise

    def test_process_invalid_json(self):
        """Ungültiges JSON soll keine Fehler verursachen."""
        streamer = FinnhubStreamer()
        streamer._process_message("not json")  # Should not raise

    def test_process_zero_price_ignored(self):
        """Preis 0 wird ignoriert."""
        streamer = FinnhubStreamer()
        msg = '{"type":"trade","data":[{"s":"AAPL","p":0,"t":1234567890,"v":100}]}'
        streamer._process_message(msg)
        assert streamer.get_price("AAPL") is None

    def test_process_updates_latest_price(self):
        """Neuerer Preis überschreibt alten."""
        streamer = FinnhubStreamer()
        msg1 = '{"type":"trade","data":[{"s":"AAPL","p":175.00,"t":1234567890,"v":100}]}'
        msg2 = '{"type":"trade","data":[{"s":"AAPL","p":176.50,"t":1234567891,"v":50}]}'
        streamer._process_message(msg1)
        streamer._process_message(msg2)
        assert streamer.get_price("AAPL") == 176.50


class TestFinnhubStreamerConnection:
    """Tests für Verbindungsstatus."""

    def test_not_connected_initially(self):
        streamer = FinnhubStreamer()
        assert not streamer.is_connected

    def test_is_connected_when_running_and_ws(self):
        streamer = FinnhubStreamer()
        streamer._running = True
        streamer._ws = MagicMock()
        assert streamer.is_connected

    def test_not_connected_when_not_running(self):
        streamer = FinnhubStreamer()
        streamer._running = False
        streamer._ws = MagicMock()
        assert not streamer.is_connected


# ==================== REST Fallback Tests ====================

@pytest.mark.asyncio
async def test_fetch_quote_no_api_key():
    """Ohne API-Key soll None zurückkommen."""
    with patch("fetchers.finnhub_ws.settings") as mock_settings:
        mock_settings.FINNHUB_API_KEY = ""
        result = await fetch_finnhub_quote("AAPL")
        assert result is None


@pytest.mark.asyncio
async def test_fetch_quote_skips_de_tickers():
    """Deutsche Ticker werden übersprungen."""
    with patch("fetchers.finnhub_ws.settings") as mock_settings:
        mock_settings.FINNHUB_API_KEY = "test_key"
        result = await fetch_finnhub_quote("SIE.DE")
        assert result is None


@pytest.mark.asyncio
async def test_fetch_quote_skips_isins():
    """ISINs werden übersprungen."""
    with patch("fetchers.finnhub_ws.settings") as mock_settings:
        mock_settings.FINNHUB_API_KEY = "test_key"
        result = await fetch_finnhub_quote("US0378331005")
        assert result is None


@pytest.mark.asyncio
async def test_fetch_quote_success():
    """Erfolgreicher REST-Quote-Abruf."""
    with patch("fetchers.finnhub_ws.settings") as mock_settings:
        mock_settings.FINNHUB_API_KEY = "test_key"

        mock_response = MagicMock()
        mock_response.json.return_value = {"c": 175.50, "h": 176.0, "l": 174.0, "o": 175.0}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("fetchers.finnhub_ws.httpx.AsyncClient") as MockAsyncClient:
            MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await fetch_finnhub_quote("AAPL")
            assert result == 175.50
