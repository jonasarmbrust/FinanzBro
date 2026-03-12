"""FinanzBro - Earnings AI Analysis (Gemini 2.5 Pro).

Analysiert die letzten/nächsten Earnings von Portfolio-Aktien
via Google Search Grounding. Ein API-Call für alle Ticker.

Output: Strukturierte Earnings-Insights (JSON) mit:
  - Status (reported/upcoming/none)
  - Beat/Miss-Info
  - Key Takeaway
"""
import json
import logging
from typing import Optional

from config import settings
from models import EarningsInsight

logger = logging.getLogger(__name__)


async def analyze_earnings(tickers: list[str]) -> list[EarningsInsight]:
    """Analysiert Earnings für die angegebenen Ticker.

    Nutzt Gemini 2.5 Pro mit Search Grounding für aktuelle Earnings-Daten.
    Ein einziger API-Call für alle Ticker.

    Returns:
        Liste von EarningsInsight-Objekten
    """
    if not settings.gemini_configured:
        return []

    if not tickers:
        return []

    try:
        from services.vertex_ai import get_client, get_grounded_config

        client = get_client()

        ticker_list = ", ".join(tickers[:15])  # Max 15 Ticker
        prompt = (
            "Analysiere die letzten oder nächsten Quartalsergebnisse (Earnings) "
            f"für folgende Aktien: {ticker_list}\n\n"
            "Für jede Aktie:\n"
            "- Wurden die letzten Earnings bereits veröffentlicht? Wenn ja, "
            "wurden die Erwartungen übertroffen (beat) oder verfehlt (miss)?\n"
            "- Was war das wichtigste Ergebnis/die wichtigste Aussage?\n"
            "- Wann sind die nächsten Earnings (falls noch nicht reported)?\n\n"
            "Antworte NUR als JSON-Array im folgenden Format:\n"
            '[{"ticker": "AAPL", "status": "reported", "quarter": "Q1 2026", '
            '"beat": true, "key_takeaway": "Revenue +8%, Services-Rekord"}, ...]\n\n'
            "status ist 'reported' (kürzlich veröffentlicht), 'upcoming' (bald), "
            "oder 'none' (keine relevanten Daten).\n"
            "beat ist true/false/null.\n"
            "key_takeaway: max 80 Zeichen, auf Deutsch.\n"
            "Kein Markdown, nur das JSON-Array."
        )

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=get_grounded_config(),
        )

        if not response.text:
            return []

        return _parse_earnings_response(response.text, tickers)

    except Exception as e:
        logger.warning(f"Earnings-Analyse fehlgeschlagen: {e}")
        return []


def _parse_earnings_response(
    text: str, tickers: list[str]
) -> list[EarningsInsight]:
    """Parst die Gemini-Antwort als JSON-Array von EarningsInsight."""
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1])

    try:
        data = json.loads(clean)
        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            if not isinstance(item, dict):
                continue
            ticker = item.get("ticker", "").upper()
            if ticker not in tickers:
                continue
            results.append(EarningsInsight(
                ticker=ticker,
                status=item.get("status", "none"),
                quarter=item.get("quarter", ""),
                beat=item.get("beat"),
                key_takeaway=str(item.get("key_takeaway", ""))[:120],
            ))
        return results

    except json.JSONDecodeError:
        logger.debug(f"Earnings JSON-Parsing fehlgeschlagen: {text[:200]}")
        return []
