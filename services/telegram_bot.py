"""FinanzBro - Telegram Bot Command Handler.

Verarbeitet eingehende Telegram-Nachrichten (Webhook).
Unterstützte Befehle:
  /portfolio — Portfolio-Übersicht mit Scores
  /score AAPL — Score einer einzelnen Aktie
  /refresh — Full Refresh triggern
  /news   — Freie Marktanalyse durch Gemini 2.5 Pro
  /start  — Willkommensnachricht
  /help   — Befehlsübersicht
"""
import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


async def handle_update(update: dict) -> None:
    """Verarbeitet ein Telegram-Update (Webhook-Payload).

    Args:
        update: Telegram Update-Objekt (JSON)
    """
    from services.telegram import send_message

    message = update.get("message", {})
    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text or not chat_id:
        return

    # Nur erlaubte Chat-ID (Sicherheit)
    if chat_id != settings.TELEGRAM_CHAT_ID:
        logger.warning(f"Unbekannte Chat-ID: {chat_id} (erwartet: {settings.TELEGRAM_CHAT_ID})")
        return

    # Command-Router
    cmd = text.split()[0].lower()
    args = text.split()[1:] if len(text.split()) > 1 else []

    if cmd == "/portfolio":
        await _cmd_portfolio(chat_id)
    elif cmd == "/score":
        ticker = args[0].upper() if args else None
        await _cmd_score(chat_id, ticker)
    elif cmd == "/refresh":
        await _cmd_refresh(chat_id)
    elif cmd == "/news":
        await _cmd_news(chat_id)
    elif cmd == "/start":
        await _cmd_start(chat_id)
    elif cmd == "/help":
        await _cmd_help(chat_id)
    else:
        # Unbekannter Befehl → Hinweis
        await send_message(
            "❓ Unbekannter Befehl. Tippe /help für eine Übersicht.",
            chat_id=chat_id,
        )


# ─────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────

async def _cmd_start(chat_id: str):
    """Willkommensnachricht."""
    from services.telegram import send_message
    await send_message(
        "🚀 *FinanzBro AI Agent*\n\n"
        "Ich bin dein persönlicher Finanzanalyst.\n\n"
        "Verfügbare Befehle:\n"
        "  /portfolio — Portfolio-Übersicht\n"
        "  /score AAPL — Score einer Aktie\n"
        "  /refresh — Daten aktualisieren\n"
        "  /news — Marktanalyse (Gemini Pro)\n"
        "  /help — Befehlsübersicht\n",
        chat_id=chat_id,
    )


async def _cmd_help(chat_id: str):
    """Befehlsübersicht."""
    from services.telegram import send_message
    await send_message(
        "📋 *FinanzBro Befehle*\n\n"
        "  /portfolio — Portfolio mit Scores und P&L\n"
        "  /score AAPL — Detail-Score einer Aktie\n"
        "  /refresh — Full Refresh starten\n"
        "  /news — Marktanalyse (Gemini 2.5 Pro)\n"
        "  /help — Diese Übersicht\n",
        chat_id=chat_id,
    )


async def _cmd_portfolio(chat_id: str):
    """Portfolio-Übersicht mit Scores."""
    from services.telegram import send_message
    from state import portfolio_data

    summary = portfolio_data.get("summary")
    if not summary or not summary.stocks:
        await send_message("⚠️ Keine Portfolio-Daten. Bitte /refresh starten.", chat_id=chat_id)
        return

    lines = ["💰 *Portfolio Übersicht*\n"]
    lines.append(f"Gesamtwert: {summary.total_value:,.2f} EUR")

    pnl_emoji = "📈" if summary.total_pnl >= 0 else "📉"
    lines.append(f"{pnl_emoji} P&L: {summary.total_pnl:+,.2f} EUR ({summary.total_pnl_percent:+.1f}%)")

    if summary.daily_total_change != 0:
        day_emoji = "🟢" if summary.daily_total_change >= 0 else "🔴"
        lines.append(f"{day_emoji} Heute: {summary.daily_total_change:+,.2f} EUR ({summary.daily_total_change_pct:+.1f}%)")

    if summary.fear_greed:
        fg = summary.fear_greed
        lines.append(f"😐 Fear&Greed: {fg.value}/100 ({fg.label})")

    # Cash-Bestand
    cash_stock = next((s for s in summary.stocks if s.position.ticker == "CASH"), None)
    if cash_stock:
        lines.append(f"💵 Cash: {cash_stock.position.current_price:,.2f} EUR")

    # FMP Usage
    try:
        from fetchers.fmp import get_fmp_usage
        usage = get_fmp_usage()
        lines.append(f"📡 FMP: {usage['requests_today']}/{usage['daily_limit']} Requests")
    except Exception:
        pass

    lines.append("\n📊 *Positionen*")

    # Sortiert nach Score
    stocks_sorted = sorted(
        [s for s in summary.stocks if s.position.ticker != "CASH"],
        key=lambda s: s.score.total_score if s.score else 0,
        reverse=True,
    )

    for stock in stocks_sorted:
        score_val = stock.score.total_score if stock.score else 0
        rating_icons = {"buy": "🟢", "hold": "🟡", "sell": "🔴"}
        icon = rating_icons.get(stock.score.rating.value, "⚪") if stock.score else "⚪"
        pnl = stock.position.pnl_percent
        daily = stock.position.daily_change_pct or 0
        daily_str = f" ({daily:+.1f}%)" if daily != 0 else ""
        lines.append(
            f"  {icon} {stock.position.ticker}: {score_val:.0f}/100"
            f" | P&L: {pnl:+.1f}%{daily_str}"
        )

    await send_message("\n".join(lines), chat_id=chat_id)


async def _cmd_score(chat_id: str, ticker: Optional[str] = None):
    """Detail-Score einer einzelnen Aktie."""
    from services.telegram import send_message
    from state import portfolio_data

    if not ticker:
        await send_message("❓ Bitte Ticker angeben: /score AAPL", chat_id=chat_id)
        return

    summary = portfolio_data.get("summary")
    if not summary or not summary.stocks:
        await send_message("⚠️ Keine Portfolio-Daten. Bitte /refresh starten.", chat_id=chat_id)
        return

    # Aktie finden
    stock = None
    for s in summary.stocks:
        if s.position.ticker.upper() == ticker:
            stock = s
            break

    if not stock:
        await send_message(f"❓ {ticker} nicht im Portfolio gefunden.", chat_id=chat_id)
        return

    if not stock.score:
        await send_message(f"⚠️ Kein Score für {ticker} verfügbar.", chat_id=chat_id)
        return

    sc = stock.score
    bd = sc.breakdown
    rating_icons = {"buy": "🟢", "hold": "🟡", "sell": "🔴"}
    icon = rating_icons.get(sc.rating.value, "⚪")

    lines = [
        f"📊 *{ticker} — Detail-Score*\n",
        f"{icon} *Gesamt: {sc.total_score:.1f}/100* ({sc.rating.value.upper()})",
        f"Confidence: {sc.confidence:.0%}\n",
        "📋 *Score-Breakdown*",
        f"  Quality:      {bd.quality_score:.0f}/100 (19%)",
        f"  Analyst:      {bd.analyst_score:.0f}/100 (15%)",
        f"  Valuation:    {bd.valuation_score:.0f}/100 (14%)",
        f"  Technical:    {bd.technical_score:.0f}/100 (13%)",
        f"  Growth:       {bd.growth_score:.0f}/100 (11%)",
        f"  Quantitative: {bd.quantitative_score:.0f}/100 (10%)",
        f"  Sentiment:    {bd.sentiment_score:.0f}/100 (7%)",
        f"  Momentum:     {bd.momentum_score:.0f}/100 (6%)",
        f"  Insider:      {bd.insider_score:.0f}/100 (3%)",
        f"  ESG:          {bd.esg_score:.0f}/100 (2%)",
    ]

    # Position-Infos
    pos = stock.position
    lines.append(f"\n💰 *Position*")
    lines.append(f"  Kurs: {pos.current_price:.2f} {pos.price_currency}")
    lines.append(f"  P&L: {pos.pnl_percent:+.1f}%")
    if pos.daily_change_pct:
        lines.append(f"  Heute: {pos.daily_change_pct:+.1f}%")

    if sc.summary:
        lines.append(f"\n📝 {sc.summary}")

    await send_message("\n".join(lines), chat_id=chat_id)


async def _cmd_refresh(chat_id: str):
    """Triggert einen Full Refresh."""
    from services.telegram import send_message
    from state import refresh_lock

    if refresh_lock.locked():
        await send_message("🔄 Refresh läuft bereits...", chat_id=chat_id)
        return

    await send_message("🔄 Full Refresh gestartet... Dies dauert ~2-3 Minuten.", chat_id=chat_id)

    try:
        from services.refresh import _refresh_data
        await _refresh_data()

        # Ergebnis melden
        from state import portfolio_data
        summary = portfolio_data.get("summary")
        if summary:
            from fetchers.fmp import get_fmp_usage
            usage = get_fmp_usage()
            await send_message(
                f"✅ Refresh abgeschlossen!\n"
                f"📊 {summary.num_positions} Positionen geladen\n"
                f"💰 Portfoliowert: {summary.total_value:,.2f} EUR\n"
                f"📡 FMP: {usage['requests_today']}/{usage['daily_limit']} Requests",
                chat_id=chat_id,
            )
        else:
            await send_message("⚠️ Refresh abgeschlossen, aber keine Daten geladen.", chat_id=chat_id)
    except Exception as e:
        logger.error(f"/refresh fehlgeschlagen: {e}")
        await send_message(f"❌ Refresh fehlgeschlagen: {e}", chat_id=chat_id)


# Rate Limiting: max 5 /news pro Stunde pro User
_news_cooldown: dict[str, list[float]] = {}
_MAX_NEWS_PER_HOUR = 5


async def _cmd_news(chat_id: str):
    """Freie Marktanalyse durch Gemini 2.5 Pro."""
    import time as _time
    from services.telegram import send_message

    if not settings.gemini_configured:
        await send_message(
            "⚠️ Gemini API-Key nicht konfiguriert.\n"
            "Bitte GEMINI_API_KEY in .env setzen.",
            chat_id=chat_id,
        )
        return

    # Rate Limiting prüfen
    now = _time.time()
    recent = [t for t in _news_cooldown.get(chat_id, []) if now - t < 3600]
    if len(recent) >= _MAX_NEWS_PER_HOUR:
        await send_message(
            f"⏳ Max {_MAX_NEWS_PER_HOUR} /news Anfragen pro Stunde. "
            "Bitte warte etwas.",
            chat_id=chat_id,
        )
        return
    _news_cooldown[chat_id] = recent + [now]

    # Lade-Hinweis senden
    await send_message("🔍 Analysiere aktuelle Marktlage mit Gemini Pro...", chat_id=chat_id)

    # Portfolio-Kontext sammeln (wenn vorhanden)
    portfolio_context = _get_portfolio_context()

    # Gemini 2.5 Pro Anfrage
    try:
        from services.vertex_ai import get_client, get_grounded_config, get_cached_content

        client = get_client()

        prompt_parts = [
            "Du bist ein erfahrener Finanzanalyst und Marktexperte. "
            "Gib eine aktuelle Marktanalyse auf Deutsch. Strukturiere deine Antwort so:\n\n"
            "1. 📰 MARKTNACHRICHTEN: Die 3-5 wichtigsten aktuellen Ereignisse an den Finanzmärkten "
            "(Zinsentscheidungen, Earnings, Geopolitik, Währungen, Rohstoffe)\n\n"
            "2. 📊 MARKTTRENDS: Aktuelle Trends bei den großen Indizes (S&P 500, NASDAQ, DAX), "
            "Sektorrotation, Volatilität\n\n"
            "3. 🔮 AUSBLICK: Kurze Einschätzung für die kommenden Tage/Wochen\n\n",
        ]

        if portfolio_context:
            prompt_parts.append(
                "4. 💼 PORTFOLIO-RELEVANZ: Wie wirken sich die aktuellen Entwicklungen "
                "auf folgendes Portfolio aus? Gib konkrete Hinweise zu einzelnen Positionen.\n\n"
                f"Portfolio:\n{portfolio_context}\n\n"
            )

        prompt_parts.append(
            "Halte dich prägnant (max 2000 Zeichen). Nutze Emojis für Übersichtlichkeit. "
            "Kein Markdown, nur Plain Text. Datum heute: "
            + __import__("datetime").datetime.now().strftime("%d.%m.%Y")
        )

        prompt = "".join(prompt_parts)

        # Search Grounding + Context Cache für echte Marktdaten
        config = get_grounded_config()
        cached = get_cached_content()
        if cached:
            config["cached_content"] = cached

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=config,
        )

        result = response.text.strip() if response.text else ""

        # Fallback: Wenn Pro rate-limited ist, versuche Flash
        if not result:
            raise Exception("Leere Antwort von Gemini Pro")

        model_used = "Gemini 2.5 Pro"

    except Exception as e:
        logger.warning(f"Gemini Pro fehlgeschlagen ({e}), versuche Flash Fallback...")

        try:
            import asyncio as _aio
            await _aio.sleep(2)  # Kurze Pause

            client_fb = get_client()
            response = client_fb.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            result = response.text.strip() if response.text else "Keine Analyse verfügbar."
            model_used = "Gemini 2.0 Flash"

        except Exception as e2:
            logger.error(f"/news komplett fehlgeschlagen: {e2}")
            await send_message(
                f"❌ Analyse fehlgeschlagen. Bitte später erneut versuchen.\n({e2})",
                chat_id=chat_id,
            )
            return

    # Header + Antwort senden
    full_message = f"📰 *FinanzBro News & Analyse*\n_{model_used}_\n\n{result}"
    await send_message(full_message, chat_id=chat_id)

    logger.info(f"✅ /news Befehl ausgeführt ({len(result)} Zeichen, {model_used})")


# ─────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────

def _get_portfolio_context() -> str:
    """Holt Portfolio-Daten als Text-Kontext für Gemini."""
    try:
        from state import portfolio_data
        summary = portfolio_data.get("summary")
        if not summary or not summary.stocks:
            return ""

        lines = []
        for stock in summary.stocks:
            if stock.position.ticker == "CASH":
                continue
            score_val = stock.score.total_score if stock.score else 0
            rating = stock.score.rating.value if stock.score else "?"
            pnl = stock.position.pnl_percent
            lines.append(
                f"  {stock.position.ticker} ({stock.position.name}) | "
                f"Score: {score_val:.0f} | {rating} | P&L: {pnl:+.1f}% | {stock.position.sector}"
            )

        return "\n".join(lines) if lines else ""
    except Exception:
        return ""
