"""FinanzBro - Finnhub Echtzeit-Kurs-Streaming

WebSocket-basierter Echtzeit-Kursfetcher über Finnhub.io.
Kostenloser Tier: US-Aktien in Echtzeit, 60 API-Calls/Min.

Features:
  - WebSocket-Streaming mit Auto-Reconnect
  - In-Memory-Preiscache (thread-safe)
  - REST-Fallback für Einzelkurse
  - Subscribe/Unsubscribe für Ticker
"""
import asyncio
import json
import logging
import time
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Finnhub endpoints
_WS_URL = "wss://ws.finnhub.io"
_REST_BASE = "https://finnhub.io/api/v1"


class FinnhubStreamer:
    """Singleton WebSocket-Client für Finnhub Echtzeit-Kurse.

    Verbindet sich zum Finnhub WebSocket, empfängt Trade-Daten
    und speichert letzte Preise in einem In-Memory-Dict.
    """

    def __init__(self):
        self._prices: dict[str, float] = {}       # ticker -> last price
        self._timestamps: dict[str, float] = {}    # ticker -> unix timestamp
        self._subscribed: set[str] = set()
        self._ws = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._reconnect_delay = 1.0  # seconds, exponential backoff

    @property
    def is_connected(self) -> bool:
        return self._running and self._ws is not None

    async def start(self):
        """Startet den WebSocket-Stream im Hintergrund."""
        api_key = settings.FINNHUB_API_KEY
        if not api_key:
            logger.info("Finnhub: Kein API-Key konfiguriert – WebSocket deaktiviert")
            return

        if self._running:
            logger.debug("Finnhub WebSocket läuft bereits")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("🔌 Finnhub WebSocket-Stream gestartet")

    async def stop(self):
        """Stoppt den WebSocket-Stream sauber."""
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        logger.info("🔌 Finnhub WebSocket-Stream gestoppt")

    def subscribe(self, tickers: list[str]):
        """Registriert Ticker für Streaming (nur US-Ticker sinnvoll)."""
        new_tickers = []
        for t in tickers:
            t = t.upper()
            # Skip non-US tickers (DE, CO, L suffixes) and ISINs
            if "." in t or (len(t) == 12 and t[:2].isalpha()):
                continue
            if t == "CASH":
                continue
            if t not in self._subscribed:
                new_tickers.append(t)
                self._subscribed.add(t)

        # Send subscribe messages if already connected
        if new_tickers and self._ws:
            asyncio.create_task(self._send_subscribes(new_tickers))

        if new_tickers:
            logger.info(f"Finnhub: {len(new_tickers)} neue Ticker abonniert: {new_tickers}")

    def unsubscribe(self, tickers: list[str]):
        """Entfernt Ticker aus dem Streaming."""
        for t in tickers:
            t = t.upper()
            self._subscribed.discard(t)
            self._prices.pop(t, None)
            self._timestamps.pop(t, None)

    def get_price(self, ticker: str) -> Optional[float]:
        """Letzten gecachten Kurs für einen Ticker."""
        return self._prices.get(ticker.upper())

    def get_all_prices(self) -> dict[str, float]:
        """Alle gecachten Kurse."""
        return dict(self._prices)

    def get_price_age(self, ticker: str) -> Optional[float]:
        """Alter des letzten Kurses in Sekunden."""
        ts = self._timestamps.get(ticker.upper())
        if ts is None:
            return None
        return time.time() - ts

    def update_price(self, ticker: str, price: float):
        """Manuelles Preis-Update (z.B. aus REST-Fallback)."""
        ticker = ticker.upper()
        self._prices[ticker] = price
        self._timestamps[ticker] = time.time()

    async def _run_loop(self):
        """Hauptschleife: Connect → Receive → Reconnect."""
        import websockets

        while self._running:
            try:
                api_key = settings.FINNHUB_API_KEY
                url = f"{_WS_URL}?token={api_key}"

                logger.info("Finnhub: Verbinde zum WebSocket...")
                async with websockets.connect(url, ping_interval=30) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0  # Reset backoff on success
                    logger.info(f"Finnhub WebSocket verbunden – abonniere {len(self._subscribed)} Ticker")

                    # Subscribe all registered tickers
                    await self._send_subscribes(list(self._subscribed))

                    # Receive loop
                    async for message in ws:
                        if not self._running:
                            break
                        self._process_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._ws = None
                if not self._running:
                    break
                logger.warning(
                    f"Finnhub WebSocket-Fehler: {e} – Reconnect in {self._reconnect_delay:.0f}s"
                )
                await asyncio.sleep(self._reconnect_delay)
                # Exponential backoff: 1s → 2s → 4s → 8s → max 30s
                self._reconnect_delay = min(self._reconnect_delay * 2, 30.0)

        self._ws = None

    async def _send_subscribes(self, tickers: list[str]):
        """Sendet Subscribe-Messages an den WebSocket."""
        if not self._ws:
            return
        for ticker in tickers:
            try:
                msg = json.dumps({"type": "subscribe", "symbol": ticker})
                await self._ws.send(msg)
            except Exception as e:
                logger.debug(f"Finnhub subscribe fehlgeschlagen für {ticker}: {e}")

    def _process_message(self, raw: str):
        """Verarbeitet eine WebSocket-Nachricht."""
        try:
            data = json.loads(raw)
            if data.get("type") == "trade" and "data" in data:
                for trade in data["data"]:
                    symbol = trade.get("s", "")
                    price = trade.get("p")
                    if symbol and price and price > 0:
                        self._prices[symbol] = round(float(price), 2)
                        self._timestamps[symbol] = time.time()
            elif data.get("type") == "ping":
                pass  # Keep-alive
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# --- Singleton Instance ---
_streamer = FinnhubStreamer()


def get_streamer() -> FinnhubStreamer:
    """Gibt die Singleton-FinnhubStreamer-Instanz zurück."""
    return _streamer


# --- REST Fallback ---

async def fetch_finnhub_quote(ticker: str) -> Optional[float]:
    """Holt einen Einzelkurs über die Finnhub REST API (Fallback).

    Returns:
        Aktueller Kurs oder None bei Fehler.
    """
    api_key = settings.FINNHUB_API_KEY
    if not api_key:
        return None

    # Skip non-US tickers
    if "." in ticker or (len(ticker) == 12 and ticker[:2].isalpha()):
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{_REST_BASE}/quote",
                params={"symbol": ticker.upper(), "token": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            price = data.get("c")  # "c" = current price
            if price and float(price) > 0:
                return round(float(price), 2)
    except Exception as e:
        logger.debug(f"Finnhub REST-Quote fehlgeschlagen für {ticker}: {e}")

    return None
