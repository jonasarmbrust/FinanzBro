"""FinanzBro - Portfolio History Engine

Speichert tägliche Portfolio-Snapshots und lädt historische Daten.
Wird nach jedem Refresh aufgerufen, um den aktuellen Stand zu protokollieren.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from config import settings

logger = logging.getLogger(__name__)

TZ_BERLIN = ZoneInfo("Europe/Berlin")
HISTORY_FILE = settings.CACHE_DIR / "portfolio_history.json"


def save_snapshot(
    total_value: float,
    total_cost: float,
    total_pnl: float,
    num_positions: int,
    eur_usd_rate: float = 1.0,
):
    """
    Speichert einen täglichen Portfolio-Snapshot.
    Maximal 1 Snapshot pro Tag (überschreibt gleichen Tag).
    """
    today = datetime.now(tz=TZ_BERLIN).strftime("%Y-%m-%d")

    history = _load_history()

    # Update or add today's snapshot
    snapshot = {
        "date": today,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "num_positions": num_positions,
        "eur_usd_rate": eur_usd_rate,
        "timestamp": datetime.now(tz=TZ_BERLIN).isoformat(),
    }

    # Replace existing entry for today or append
    updated = False
    for i, entry in enumerate(history):
        if entry.get("date") == today:
            history[i] = snapshot
            updated = True
            break

    if not updated:
        history.append(snapshot)

    # Keep max 365 days of history
    if len(history) > 365:
        history = history[-365:]

    # Sort by date
    history.sort(key=lambda x: x["date"])

    _save_history(history)
    logger.info(f"📸 Portfolio-Snapshot gespeichert für {today}: ${total_value:,.2f}")


def load_history(days: int = 90) -> list[dict]:
    """
    Lädt historische Portfolio-Snapshots.

    Args:
        days: Anzahl Tage zurück (Standard: 90)

    Returns:
        Liste von Snapshots [{date, total_value, total_cost, total_pnl, ...}]
    """
    history = _load_history()

    if days > 0:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        history = [h for h in history if h.get("date", "") >= cutoff]

    return history


def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _save_history(history: list[dict]):
    HISTORY_FILE.write_text(
        json.dumps(history, indent=2, default=str),
        encoding="utf-8",
    )
