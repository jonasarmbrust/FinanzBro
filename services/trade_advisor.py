"""FinanzBro - AI Trade Advisor.

Evaluiert Kauf/Verkauf/Aufstocken-Entscheidungen mit:
  - Gemini 2.5 Pro (AI-Analyse + Google Search Grounding)
  - 10-Faktor Scoring-Engine (live oder aus Cache)
  - Portfolio-Kontext (Sektoren, Gewichtung, Diversifikation)
  - Optionale externe Quellen (Analysten, Artikel, User-Notizen)
"""
import json
import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


async def evaluate_trade(
    ticker: str,
    action: str = "buy",
    amount_eur: Optional[float] = None,
    extra_context: Optional[str] = None,
) -> dict:
    """Evaluiert eine Trade-Entscheidung mit AI + Portfolio-Kontext.

    Args:
        ticker: Aktien-Ticker (z.B. "NVDA", "AAPL")
        action: "buy" (Neukauf), "sell" (Verkauf), "increase" (Aufstocken)
        amount_eur: Geplanter Betrag in EUR (optional)
        extra_context: Zusätzliche Informationen vom User (Analysten, Artikel)

    Returns:
        dict mit AI-Bewertung, Score, Portfolio-Impact, Risiken
    """
    from state import portfolio_data

    if not settings.gemini_configured:
        return {
            "error": "Gemini API nicht konfiguriert. Bitte GEMINI_API_KEY setzen.",
            "recommendation": "unknown",
        }

    summary = portfolio_data.get("summary")
    if not summary or not summary.stocks:
        return {
            "error": "Keine Portfolio-Daten vorhanden. Bitte zuerst einen Refresh starten.",
            "recommendation": "unknown",
        }

    ticker = ticker.upper().strip()
    action = action.lower().strip()
    if action not in ("buy", "sell", "increase"):
        action = "buy"

    # 1. Score berechnen (live oder aus Cache)
    score_info = await _get_or_calculate_score(ticker, summary)

    # 2. Portfolio-Kontext aufbauen
    portfolio_ctx = _build_portfolio_context(summary, ticker, action, amount_eur)

    # 3. Gemini-Prompt erstellen
    prompt = _build_advisor_prompt(
        ticker=ticker,
        action=action,
        amount_eur=amount_eur,
        score_info=score_info,
        portfolio_ctx=portfolio_ctx,
        extra_context=extra_context,
    )

    # 4. AI-Analyse via Gemini 2.5 Pro
    try:
        result = await _call_gemini(prompt)
        result["ticker"] = ticker
        result["action"] = action
        result["amount_eur"] = amount_eur
        result["score"] = score_info
        result["portfolio_context"] = portfolio_ctx
        return result
    except Exception as e:
        logger.error(f"Trade Advisor Fehler: {e}")
        return {
            "error": str(e),
            "ticker": ticker,
            "action": action,
            "score": score_info,
            "portfolio_context": portfolio_ctx,
            "recommendation": "unknown",
        }


# ─────────────────────────────────────────────────────────────
# Score-Berechnung
# ─────────────────────────────────────────────────────────────

async def _get_or_calculate_score(ticker: str, summary) -> dict:
    """Holt Score aus Portfolio-Cache oder berechnet ihn live."""
    # Prüfe ob Ticker im Portfolio ist
    for stock in summary.stocks:
        if stock.position.ticker == ticker and stock.score:
            s = stock.score
            return {
                "total_score": s.total_score,
                "rating": s.rating.value,
                "confidence": s.confidence,
                "in_portfolio": True,
                "current_weight": round(
                    stock.position.current_value / summary.total_value * 100, 1
                ) if summary.total_value > 0 else 0,
                "current_pnl_pct": stock.position.pnl_percent,
                "breakdown": {
                    "quality": s.breakdown.quality_score,
                    "valuation": s.breakdown.valuation_score,
                    "analyst": s.breakdown.analyst_score,
                    "technical": s.breakdown.technical_score,
                    "momentum": s.breakdown.momentum_score,
                    "sentiment": s.breakdown.sentiment_score,
                },
            }

    # Nicht im Portfolio → Live-Score berechnen
    try:
        from services.data_loader import load_position_data
        from models import PortfolioPosition
        from fetchers.fear_greed import fetch_fear_greed_index

        fear_greed = summary.fear_greed
        if not fear_greed:
            try:
                fear_greed = await fetch_fear_greed_index()
            except Exception:
                pass

        dummy_pos = PortfolioPosition(
            ticker=ticker,
            name=ticker,
            shares=0,
            avg_cost=0,
            current_price=0,
        )
        stock_data = await load_position_data(dummy_pos, fear_greed)

        if stock_data.score:
            s = stock_data.score
            return {
                "total_score": s.total_score,
                "rating": s.rating.value,
                "confidence": s.confidence,
                "in_portfolio": False,
                "current_weight": 0,
                "current_pnl_pct": 0,
                "name": stock_data.position.name,
                "sector": stock_data.position.sector,
                "breakdown": {
                    "quality": s.breakdown.quality_score,
                    "valuation": s.breakdown.valuation_score,
                    "analyst": s.breakdown.analyst_score,
                    "technical": s.breakdown.technical_score,
                    "momentum": s.breakdown.momentum_score,
                    "sentiment": s.breakdown.sentiment_score,
                },
            }
    except Exception as e:
        logger.warning(f"Live-Score für {ticker} fehlgeschlagen: {e}")

    return {
        "total_score": None,
        "rating": "unknown",
        "in_portfolio": False,
        "confidence": 0,
        "current_weight": 0,
    }


# ─────────────────────────────────────────────────────────────
# Portfolio-Kontext
# ─────────────────────────────────────────────────────────────

def _build_portfolio_context(summary, ticker: str, action: str, amount_eur: Optional[float]) -> dict:
    """Baut Portfolio-Kontext für die AI-Analyse."""
    total = summary.total_value or 1
    stocks = [s for s in summary.stocks if s.position.ticker != "CASH"]

    # Sektor-Verteilung
    sectors = {}
    for s in stocks:
        sec = s.position.sector or "Unknown"
        sectors[sec] = sectors.get(sec, 0) + s.position.current_value
    sector_pcts = {k: round(v / total * 100, 1) for k, v in sectors.items()}

    # Aktuelle Positionen (Top 10 nach Gewicht)
    positions = []
    for s in sorted(stocks, key=lambda x: x.position.current_value, reverse=True)[:10]:
        positions.append({
            "ticker": s.position.ticker,
            "name": s.position.name,
            "weight": round(s.position.current_value / total * 100, 1),
            "score": s.score.total_score if s.score else None,
            "rating": s.score.rating.value if s.score else "unknown",
            "pnl_pct": s.position.pnl_percent,
            "sector": s.position.sector,
        })

    # Impact-Simulation
    impact = {}
    if amount_eur and amount_eur > 0:
        target_ticker_sector = None
        for s in summary.stocks:
            if s.position.ticker == ticker:
                target_ticker_sector = s.position.sector
                break

        new_total = total + amount_eur if action != "sell" else total - amount_eur
        if new_total > 0 and target_ticker_sector:
            old_sector_pct = sector_pcts.get(target_ticker_sector, 0)
            sector_value = sectors.get(target_ticker_sector, 0)
            if action == "sell":
                new_sector_value = sector_value - amount_eur
            else:
                new_sector_value = sector_value + amount_eur
            new_sector_pct = round(new_sector_value / new_total * 100, 1)
            impact = {
                "sector": target_ticker_sector,
                "sector_weight_before": old_sector_pct,
                "sector_weight_after": new_sector_pct,
                "portfolio_value_after": round(new_total, 2),
            }

    return {
        "total_value": round(total, 2),
        "num_positions": len(stocks),
        "total_pnl_pct": summary.total_pnl_percent,
        "fear_greed": summary.fear_greed.value if summary.fear_greed else None,
        "fear_greed_label": summary.fear_greed.label if summary.fear_greed else None,
        "sector_distribution": sector_pcts,
        "top_positions": positions,
        "impact": impact,
    }


# ─────────────────────────────────────────────────────────────
# Gemini Prompt
# ─────────────────────────────────────────────────────────────

def _build_advisor_prompt(
    ticker: str,
    action: str,
    amount_eur: Optional[float],
    score_info: dict,
    portfolio_ctx: dict,
    extra_context: Optional[str],
) -> str:
    """Baut den strukturierten Prompt für Gemini 2.5 Pro."""
    action_de = {"buy": "Kauf", "sell": "Verkauf", "increase": "Aufstocken"}.get(action, action)

    lines = [
        "Du bist ein erfahrener Portfolio-Advisor. Analysiere die folgende Trade-Idee "
        "im Kontext des bestehenden Portfolios. Antworte auf Deutsch.",
        "",
        "═══════════════════════════════════════",
        f"TRADE-ANFRAGE: {action_de.upper()} von {ticker}",
        "═══════════════════════════════════════",
        "",
    ]

    if amount_eur:
        lines.append(f"Geplanter Betrag: {amount_eur:,.0f} EUR")
    lines.append(f"Aktion: {action_de}")
    lines.append("")

    # Score-Info
    if score_info.get("total_score") is not None:
        lines.append(f"── SCORING-ENGINE ERGEBNIS ──")
        lines.append(f"10-Faktor-Score: {score_info['total_score']:.0f}/100 ({score_info['rating'].upper()})")
        lines.append(f"Confidence: {score_info.get('confidence', 0):.0%}")
        if score_info.get("in_portfolio"):
            lines.append(f"Aktuelles Gewicht: {score_info['current_weight']:.1f}%")
            lines.append(f"Aktuelle P&L: {score_info['current_pnl_pct']:+.1f}%")
        bd = score_info.get("breakdown", {})
        if bd:
            lines.append(f"  Quality: {bd.get('quality', 0):.0f} | Valuation: {bd.get('valuation', 0):.0f} | "
                         f"Analyst: {bd.get('analyst', 0):.0f}")
            lines.append(f"  Technical: {bd.get('technical', 0):.0f} | Momentum: {bd.get('momentum', 0):.0f} | "
                         f"Sentiment: {bd.get('sentiment', 0):.0f}")
    else:
        lines.append(f"⚠️ Kein Score verfügbar — bitte recherchiere {ticker} selbst.")
    lines.append("")

    # Portfolio-Kontext
    lines.append("── PORTFOLIO-KONTEXT ──")
    lines.append(f"Gesamtwert: {portfolio_ctx['total_value']:,.0f} EUR ({portfolio_ctx['num_positions']} Positionen)")
    lines.append(f"Gesamt-P&L: {portfolio_ctx['total_pnl_pct']:+.1f}%")
    if portfolio_ctx.get("fear_greed"):
        lines.append(f"Markt-Sentiment (Fear&Greed): {portfolio_ctx['fear_greed']}/100 ({portfolio_ctx['fear_greed_label']})")
    lines.append("")

    lines.append("Sektor-Verteilung:")
    for sec, pct in sorted(portfolio_ctx["sector_distribution"].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {sec}: {pct:.1f}%")
    lines.append("")

    lines.append("Top-Positionen:")
    for p in portfolio_ctx["top_positions"][:8]:
        score_str = f"Score: {p['score']:.0f}" if p["score"] else "kein Score"
        lines.append(f"  {p['ticker']} ({p['name']}) — {p['weight']:.1f}% | {score_str} | P&L: {p['pnl_pct']:+.1f}%")
    lines.append("")

    # Impact
    impact = portfolio_ctx.get("impact", {})
    if impact:
        lines.append("── IMPACT-SIMULATION ──")
        lines.append(f"Sektor {impact['sector']}: {impact['sector_weight_before']:.1f}% → {impact['sector_weight_after']:.1f}%")
        lines.append("")

    # Externe Quellen
    if extra_context and extra_context.strip():
        lines.append("── EXTERNE QUELLEN (vom User) ──")
        # Auf 3000 Zeichen begrenzen
        lines.append(extra_context.strip()[:3000])
        lines.append("")

    # Aufgabe
    lines.append("═══════════════════════════════════════")
    lines.append("AUFGABE:")
    lines.append("═══════════════════════════════════════")
    lines.append("")
    lines.append(
        "Erstelle eine professionelle Trade-Bewertung. Antworte STRIKT im folgenden JSON-Format "
        "(kein Markdown, kein Code-Block, nur reines JSON):\n"
    )
    lines.append("""{
  "recommendation": "buy" | "hold" | "reduce" | "avoid",
  "confidence": <0-100>,
  "summary": "<1-2 Sätze Fazit>",
  "bull_case": "<Argumente für den Trade>",
  "bear_case": "<Argumente gegen den Trade>",
  "portfolio_fit": "<Wie passt der Trade zum Portfolio? Diversifikation, Sektor-Overlap, Korrelation>",
  "sizing_advice": "<Empfohlene Positionsgröße und Begründung>",
  "risks": ["<Risiko 1>", "<Risiko 2>", "<Risiko 3>"],
  "timing": "<Ist der Zeitpunkt günstig? Momentum, Sentiment, Makro>",
  "external_analysis": "<Falls externe Quellen vorhanden: Zusammenfassung und Einordnung>"
}""")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Gemini API Call
# ─────────────────────────────────────────────────────────────

async def _call_gemini(prompt: str) -> dict:
    """Ruft Gemini 2.5 Pro mit Google Search Grounding auf."""
    from services.vertex_ai import get_client, get_grounded_config, get_cached_content

    client = get_client()

    # Google Search Grounding + Context Cache
    config = get_grounded_config()
    cached = get_cached_content()
    if cached:
        config["cached_content"] = cached

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=config,
    )

    raw = response.text.strip() if response.text else ""
    logger.info(f"🧠 Trade Advisor Response für {prompt[:50]}... ({len(raw)} Zeichen)")

    # JSON parsen (Gemini liefert manchmal Markdown Code-Blocks)
    return _parse_ai_response(raw)


def _parse_ai_response(raw: str) -> dict:
    """Parsed die Gemini-Antwort zu strukturiertem Dict."""
    # Markdown Code-Blocks entfernen
    cleaned = raw
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1]
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        # Sicherstellen dass alle erwarteten Felder vorhanden
        defaults = {
            "recommendation": "hold",
            "confidence": 50,
            "summary": "",
            "bull_case": "",
            "bear_case": "",
            "portfolio_fit": "",
            "sizing_advice": "",
            "risks": [],
            "timing": "",
            "external_analysis": "",
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default
        return result
    except json.JSONDecodeError:
        logger.warning(f"JSON-Parsing fehlgeschlagen, verwende Freitext")
        return {
            "recommendation": "hold",
            "confidence": 50,
            "summary": raw[:500],
            "bull_case": "",
            "bear_case": "",
            "portfolio_fit": "",
            "sizing_advice": "",
            "risks": [],
            "timing": "",
            "external_analysis": "",
            "raw_response": raw,
        }
