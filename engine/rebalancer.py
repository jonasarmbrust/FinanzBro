"""FinanzBro - Rebalancing Engine v2

Berechnet Portfolio-Rebalancing Empfehlungen basierend auf:
- Aktueller Allokation vs. Ziel-Allokation
- Stock Scores (kontinuierliche Kurve statt 3 Stufen)
- Sektor-Diversifikation (max. 35% pro Sektor)
- Risiko-Anpassung via Beta
- Prioritätsbasierte Sortierung

v2 Änderungen:
  - CASH-Position ausgefiltert
  - Sektor-Konzentrationslimits (35%)
  - Beta-adjustierte Gewichtung
  - Kontinuierliche Score-Kurve
  - Höhere Schwelle (1.5% statt 0.5%)
  - Reichhaltige, actionable Begründungen
  - Prioritäts-Berechnung (1-10)
"""
import logging
from typing import Optional

from models import (
    PortfolioPosition,
    Rating,
    RebalancingAction,
    RebalancingAdvice,
    StockScore,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Konfiguration
# ─────────────────────────────────────────────────────────────

MAX_SINGLE_WEIGHT = 0.15   # 15% max pro Einzelaktie
MIN_SINGLE_WEIGHT = 0.03   # 3% min pro Einzelaktie
MAX_SECTOR_WEIGHT = 0.35   # 35% max pro Sektor
REBALANCE_THRESHOLD = 0.015  # 1.5% Mindestabweichung für Aktion

# Beta-Grenzen für Risk-Adjustment
BETA_NEUTRAL = 1.0
BETA_MAX_PENALTY = 2.0  # Ab Beta 2.0+ → maximale Reduktion
BETA_WEIGHT_FLOOR = 0.6  # Minimaler Beta-Multiplikator


def calculate_rebalancing(
    positions: list[PortfolioPosition],
    scores: dict[str, StockScore],
    target_weights: Optional[dict[str, float]] = None,
    stocks: Optional[list] = None,  # list[StockFullData] für Sektor/Beta
) -> RebalancingAdvice:
    """
    Berechnet Rebalancing-Empfehlungen.

    Args:
        positions: Aktuelle Portfolio-Positionen
        scores: Stock Scores pro Ticker
        target_weights: Optionale benutzerdefinierte Ziel-Gewichtungen (0-1)
        stocks: StockFullData-Liste für erweiterte Daten (Sektor, Beta)

    Returns:
        RebalancingAdvice mit empfohlenen Aktionen
    """
    if not positions:
        return RebalancingAdvice(summary="Keine Positionen im Portfolio")

    # CASH-Position ausfiltern
    stock_positions = [p for p in positions if p.ticker != "CASH"]
    if not stock_positions:
        return RebalancingAdvice(summary="Nur Cash im Portfolio")

    # Calculate total portfolio value (nur Aktien)
    total_value = sum(p.current_value for p in stock_positions)
    if total_value <= 0:
        return RebalancingAdvice(summary="Portfoliowert ist 0")

    # Build lookup maps für erweiterte Daten
    beta_map = {}
    sector_map = {}
    fundamentals_map = {}
    analyst_map = {}
    if stocks:
        for s in stocks:
            t = s.position.ticker
            if t == "CASH":
                continue
            sector_map[t] = s.position.sector or "Unknown"
            if s.fundamentals and s.fundamentals.beta is not None:
                beta_map[t] = s.fundamentals.beta
            if s.analyst:
                analyst_map[t] = s.analyst
    else:
        # Fallback: Sektor aus Position
        for p in stock_positions:
            sector_map[p.ticker] = p.sector or "Unknown"

    # Score-Änderungen aus History laden
    score_changes = _load_score_changes(scores)

    # Calculate current weights
    current_weights = {}
    for p in stock_positions:
        current_weights[p.ticker] = p.current_value / total_value

    # Determine target weights
    if target_weights:
        t_weights = target_weights
    else:
        t_weights = _calculate_smart_weights(
            stock_positions, scores, beta_map, sector_map,
        )

    # Sektor-Analyse & Warnungen
    sector_weights = _calculate_sector_weights(current_weights, sector_map)
    sector_warnings = []
    for sector, weight in sector_weights.items():
        if weight > MAX_SECTOR_WEIGHT:
            pct = round(weight * 100, 1)
            limit_pct = round(MAX_SECTOR_WEIGHT * 100, 0)
            sector_warnings.append(
                f"⚠️ {sector}: {pct}% > {limit_pct:.0f}% Limit"
            )

    # Calculate rebalancing actions
    actions = []
    for p in stock_positions:
        ticker = p.ticker
        current_w = current_weights.get(ticker, 0)
        target_w = t_weights.get(ticker, current_w)
        score = scores.get(ticker)

        diff_w = target_w - current_w
        diff_amount = diff_w * total_value

        # Determine action (höhere Schwelle: 1.5%)
        if abs(diff_w) < REBALANCE_THRESHOLD:
            action_str = "Halten"
        elif diff_w > 0:
            action_str = "Kaufen"
        else:
            action_str = "Verkaufen"

        # Calculate share delta
        shares_delta = 0.0
        if p.current_price > 0:
            shares_delta = diff_amount / p.current_price

        # Build detailed reasons
        reasons = _build_reasons(
            ticker, current_w, target_w, score,
            sector_map.get(ticker, ""),
            sector_weights,
            beta_map.get(ticker),
            analyst_map.get(ticker),
            score_changes.get(ticker),
        )

        # Legacy reason (erster Grund als String)
        reason = " | ".join(reasons[:3]) if reasons else "Keine Änderung"

        # Priorität berechnen (1-10)
        priority = _calculate_priority(
            diff_w, score, action_str, sector_map.get(ticker, ""),
            sector_weights,
        )

        actions.append(RebalancingAction(
            ticker=ticker,
            name=p.name,
            current_weight=round(current_w * 100, 1),
            target_weight=round(target_w * 100, 1),
            action=action_str,
            amount_eur=round(abs(diff_amount), 2),
            shares_delta=round(shares_delta, 2),
            rating=score.rating if score else Rating.HOLD,
            reason=reason,
            priority=priority,
            sector=sector_map.get(ticker, ""),
            score=score.total_score if score else 0.0,
            score_change=score_changes.get(ticker),
            reasons=reasons,
        ))

    # Sort: Höchste Priorität zuerst, dann nach Betrag
    actions.sort(key=lambda a: (-a.priority, -abs(a.amount_eur)))

    # Gesamtbeträge berechnen
    total_buy = sum(a.amount_eur for a in actions if a.action == "Kaufen")
    total_sell = sum(a.amount_eur for a in actions if a.action == "Verkaufen")

    # Build summary
    buys = [a for a in actions if a.action == "Kaufen"]
    sells = [a for a in actions if a.action == "Verkaufen"]
    holds = [a for a in actions if a.action == "Halten"]

    summary_parts = []
    if sells:
        summary_parts.append(f"📉 {len(sells)}× Reduzieren (€{total_sell:,.0f})")
    if buys:
        summary_parts.append(f"📈 {len(buys)}× Aufstocken (€{total_buy:,.0f})")
    if holds:
        summary_parts.append(f"✅ {len(holds)}× Halten")

    if sector_warnings:
        summary_parts.append(f"⚠️ {len(sector_warnings)} Sektor-Warnung{'en' if len(sector_warnings) > 1 else ''}")

    summary = " | ".join(summary_parts) if summary_parts else "Portfolio ist gut ausbalanciert ✅"

    return RebalancingAdvice(
        total_value=round(total_value, 2),
        actions=actions,
        summary=summary,
        sector_warnings=sector_warnings,
        total_buy_amount=round(total_buy, 2),
        total_sell_amount=round(total_sell, 2),
        net_rebalance=round(total_buy - total_sell, 2),
    )


# ─────────────────────────────────────────────────────────────
# Smart Weights: Score + Beta + Sektor
# ─────────────────────────────────────────────────────────────

def _calculate_smart_weights(
    positions: list[PortfolioPosition],
    scores: dict[str, StockScore],
    beta_map: dict[str, float] = None,
    sector_map: dict[str, str] = None,
) -> dict[str, float]:
    """
    Berechnet intelligente Ziel-Gewichtungen.

    1. Basis: Gleichgewichtung
    2. Score-Multiplikator: kontinuierliche Kurve (0.5 + score/100)
    3. Beta-Adjustment: High-Beta → niedrigere Gewichtung
    4. Sektor-Limits: Max. 35% pro Sektor
    5. Min/Max Caps: 3-15% pro Einzelaktie
    """
    n = len(positions)
    if n == 0:
        return {}

    beta_map = beta_map or {}
    sector_map = sector_map or {}

    base_weight = 1.0 / n

    # Step 1: Score-basierte Gewichtung (kontinuierliche Kurve)
    raw_weights = {}
    for p in positions:
        score = scores.get(p.ticker)
        if score:
            # Kontinuierliche Kurve: Score 0→0.5×, Score 50→1.0×, Score 100→1.5×
            score_mult = 0.5 + (score.total_score / 100.0)
        else:
            score_mult = 1.0

        # Step 2: Beta-Adjustment
        beta = beta_map.get(p.ticker, BETA_NEUTRAL)
        if beta > 0:
            # Inverse: Beta 0.5→1.4×, Beta 1.0→1.0×, Beta 2.0→0.6×
            beta_mult = max(BETA_WEIGHT_FLOOR, BETA_NEUTRAL / max(beta, 0.5))
        else:
            beta_mult = 1.0

        raw_weights[p.ticker] = base_weight * score_mult * beta_mult

    # Step 3: Normalize to sum = 1.0
    total_raw = sum(raw_weights.values())
    if total_raw > 0:
        normalized = {k: v / total_raw for k, v in raw_weights.items()}
    else:
        normalized = {p.ticker: base_weight for p in positions}

    # Step 4: Min/Max Caps
    for ticker in normalized:
        normalized[ticker] = max(MIN_SINGLE_WEIGHT, min(MAX_SINGLE_WEIGHT, normalized[ticker]))

    # Re-normalize nach Caps
    total = sum(normalized.values())
    if total > 0:
        normalized = {k: v / total for k, v in normalized.items()}

    # Step 5: Sektor-Limits
    normalized = _apply_sector_limits(normalized, sector_map)

    return normalized


def _apply_sector_limits(
    weights: dict[str, float],
    sector_map: dict[str, str],
) -> dict[str, float]:
    """Reduziert Gewichte wenn ein Sektor > MAX_SECTOR_WEIGHT ist."""
    if not sector_map:
        return weights

    # Berechne Sektor-Gewichte
    sector_weights = _calculate_sector_weights(weights, sector_map)

    # Prüfe ob ein Sektor über dem Limit liegt
    needs_adjustment = False
    for sector, sw in sector_weights.items():
        if sw > MAX_SECTOR_WEIGHT + 0.01:  # Kleine Toleranz
            needs_adjustment = True
            break

    if not needs_adjustment:
        return weights

    # Iterativ reduzieren (max 5 Iterationen)
    adjusted = dict(weights)
    for _ in range(5):
        sector_weights = _calculate_sector_weights(adjusted, sector_map)
        any_over = False

        for sector, sw in sector_weights.items():
            if sw > MAX_SECTOR_WEIGHT + 0.01:
                any_over = True
                # Finde Ticker in diesem Sektor
                sector_tickers = [t for t, s in sector_map.items() if s == sector and t in adjusted]
                if not sector_tickers:
                    continue

                # Reduziere proportional
                reduction_factor = MAX_SECTOR_WEIGHT / sw
                for t in sector_tickers:
                    adjusted[t] *= reduction_factor

        if not any_over:
            break

    # Re-normalize
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: v / total for k, v in adjusted.items()}

    return adjusted


def _calculate_sector_weights(
    weights: dict[str, float],
    sector_map: dict[str, str],
) -> dict[str, float]:
    """Berechnet die Gewichtung pro Sektor."""
    sector_weights: dict[str, float] = {}
    for ticker, weight in weights.items():
        sector = sector_map.get(ticker, "Unknown")
        sector_weights[sector] = sector_weights.get(sector, 0) + weight
    return sector_weights


# ─────────────────────────────────────────────────────────────
# Priority
# ─────────────────────────────────────────────────────────────

def _calculate_priority(
    diff_w: float,
    score: Optional[StockScore],
    action: str,
    sector: str,
    sector_weights: dict[str, float],
) -> int:
    """Berechnet Priorität 1-10 für eine Rebalancing-Aktion.

    Hohe Priorität:
    - SELL-rated + übergewichtet
    - BUY-rated + untergewichtet
    - Sektor über Limit

    Niedrige Priorität:
    - Halten
    - Kleine Differenzen
    """
    if action == "Halten":
        return 1

    prio = 3  # Basis

    # Größe der Abweichung (0-3 Punkte)
    abs_diff = abs(diff_w)
    if abs_diff > 0.05:
        prio += 3
    elif abs_diff > 0.03:
        prio += 2
    elif abs_diff > 0.015:
        prio += 1

    # Score-Signal verstärkt Prio
    if score:
        if action == "Verkaufen" and score.rating == Rating.SELL:
            prio += 2  # SELL-rated + übergewichtet = dringend!
        elif action == "Kaufen" and score.rating == Rating.BUY:
            prio += 2  # BUY-rated + untergewichtet = Gelegenheit!
        elif action == "Verkaufen" and score.rating == Rating.BUY:
            prio -= 1  # BUY-rated aber übergewichtet = weniger dringend

    # Sektor über Limit → +1
    sw = sector_weights.get(sector, 0)
    if sw > MAX_SECTOR_WEIGHT and action == "Verkaufen":
        prio += 1

    return max(1, min(10, prio))


# ─────────────────────────────────────────────────────────────
# Begründungen
# ─────────────────────────────────────────────────────────────

def _build_reasons(
    ticker: str,
    current_w: float,
    target_w: float,
    score: Optional[StockScore],
    sector: str,
    sector_weights: dict[str, float],
    beta: Optional[float],
    analyst: Optional[object],  # AnalystData
    score_change: Optional[float],
) -> list[str]:
    """Erstellt detaillierte, actionable Begründungen."""
    reasons = []
    diff_pct = (target_w - current_w) * 100

    # 1. Gewichtungs-Abweichung
    if abs(diff_pct) < 1.5:
        reasons.append("✅ Gewichtung passt")
    elif diff_pct > 0:
        reasons.append(f"📉 Untergewichtet ({current_w*100:.1f}% → {target_w*100:.1f}%)")
    else:
        reasons.append(f"📈 Übergewichtet ({current_w*100:.1f}% → {target_w*100:.1f}%)")

    # 2. Score-Kontext
    if score:
        emoji = {"buy": "🟢", "hold": "🟡", "sell": "🔴"}[score.rating.value]
        score_str = f"Score: {score.total_score:.0f}/100 {emoji}"
        if score_change is not None and abs(score_change) >= 3:
            arrow = "↑" if score_change > 0 else "↓"
            score_str += f" ({arrow}{abs(score_change):.0f})"
        reasons.append(score_str)

    # 3. Sektor-Warnung
    sw = sector_weights.get(sector, 0)
    if sw > MAX_SECTOR_WEIGHT:
        reasons.append(f"⚠️ {sector}: {sw*100:.0f}% > {MAX_SECTOR_WEIGHT*100:.0f}% Limit")

    # 4. Beta-Risiko
    if beta is not None and abs(beta - 1.0) > 0.3:
        if beta > 1.3:
            reasons.append(f"⚡ High Beta ({beta:.1f}) → reduzierte Gewichtung")
        elif beta < 0.7:
            reasons.append(f"🛡️ Low Beta ({beta:.1f}) → defensiv")

    # 5. Analysten-Kontext
    if analyst and hasattr(analyst, 'num_analysts') and analyst.num_analysts > 0:
        parts = []
        if analyst.consensus:
            parts.append(analyst.consensus)
        if analyst.target_price and analyst.target_price > 0:
            parts.append(f"Ziel: €{analyst.target_price:.0f}")
        if parts:
            reasons.append(f"👨‍💼 Analysten ({analyst.num_analysts}): {', '.join(parts)}")

    return reasons


# ─────────────────────────────────────────────────────────────
# Score-Änderungen (aus History)
# ─────────────────────────────────────────────────────────────

def _load_score_changes(scores: dict[str, StockScore]) -> dict[str, float]:
    """Lädt Score-Änderungen seit der letzten Analyse."""
    try:
        from engine.analysis import _get_latest_scores
        previous = _get_latest_scores()
        changes = {}
        for ticker, score in scores.items():
            prev = previous.get(ticker)
            if prev is not None:
                changes[ticker] = round(score.total_score - prev, 1)
        return changes
    except Exception:
        return {}
