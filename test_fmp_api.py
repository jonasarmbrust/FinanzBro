"""FMP Stable API - Smoke Test

Testet alle FMP API Endpoints gegen die Stable API.
Benötigt einen gültigen FMP_API_KEY in .env.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings


async def run_tests():
    """Führt Smoke Tests für alle FMP Endpoints durch."""
    from fetchers.fmp import (
        get_company_profile,
        get_key_metrics,
        get_financial_ratios,
        get_stock_quote,
        get_rating_snapshot,
        get_financial_scores,
        get_upgrades_downgrades_consensus,
        get_price_target_summary,
        fetch_fundamentals,
        fetch_analyst_data,
        fetch_fmp_rating,
        clear_cache,
    )

    # Clear cache to force fresh API calls
    clear_cache()

    ticker = "AAPL"
    results = {}

    print(f"\n{'='*60}")
    print(f"  FMP Stable API Smoke Test")
    print(f"  Ticker: {ticker}")
    print(f"  Demo Mode: {settings.demo_mode}")
    print(f"  Base URL: {settings.FMP_BASE_URL}")
    print(f"{'='*60}\n")

    if settings.demo_mode:
        print("⚠️  Demo Mode aktiv - alle Endpoints geben None zurück.")
        print("    Setze FMP_API_KEY in .env für Live-Tests.\n")

    # --- Test raw endpoints ---
    tests = [
        ("Company Profile", get_company_profile, ticker),
        ("Key Metrics TTM", get_key_metrics, ticker),
        ("Financial Ratios TTM", get_financial_ratios, ticker),
        ("Stock Quote", get_stock_quote, ticker),
        ("Rating Snapshot", get_rating_snapshot, ticker),
        ("Financial Scores", get_financial_scores, ticker),
        ("Upgrades/Downgrades Consensus", get_upgrades_downgrades_consensus, ticker),
        ("Price Target Summary", get_price_target_summary, ticker),
    ]

    for name, func, arg in tests:
        try:
            result = await func(arg)
            if settings.demo_mode:
                # In demo mode, None is expected
                status = "✅ PASS (None - Demo Mode)" if result is None else "⚠️  UNEXPECTED"
            else:
                if result is not None:
                    status = f"✅ PASS ({len(result) if isinstance(result, dict) else '?'} Felder)"
                else:
                    status = "❌ FAIL (None)"
            results[name] = result is not None or settings.demo_mode
        except Exception as e:
            status = f"❌ ERROR: {e}"
            results[name] = False
        print(f"  {status:50s} | {name}")

    # --- Test high-level functions ---
    print(f"\n{'─'*60}")
    print("  High-Level Aggregations:\n")

    try:
        fund = await fetch_fundamentals(ticker)
        has_extra = fund.altman_z_score is not None or fund.piotroski_score is not None
        extra = f" (Z={fund.altman_z_score}, Piotroski={fund.piotroski_score})" if has_extra else ""
        print(f"  ✅ fetch_fundamentals{extra}")
        results["fetch_fundamentals"] = True
    except Exception as e:
        print(f"  ❌ fetch_fundamentals: {e}")
        results["fetch_fundamentals"] = False

    try:
        analyst = await fetch_analyst_data(ticker)
        print(f"  ✅ fetch_analyst_data (Consensus={analyst.consensus}, Analysts={analyst.num_analysts})")
        results["fetch_analyst_data"] = True
    except Exception as e:
        print(f"  ❌ fetch_analyst_data: {e}")
        results["fetch_analyst_data"] = False

    try:
        rating = await fetch_fmp_rating(ticker)
        if rating:
            print(f"  ✅ fetch_fmp_rating (Rating={rating.rating}, Score={rating.rating_score})")
        else:
            print(f"  {'✅' if settings.demo_mode else '❌'} fetch_fmp_rating (None)")
        results["fetch_fmp_rating"] = rating is not None or settings.demo_mode
    except Exception as e:
        print(f"  ❌ fetch_fmp_rating: {e}")
        results["fetch_fmp_rating"] = False

    # --- Summary ---
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Ergebnis: {passed}/{total} Tests bestanden")
    if passed == total:
        print("  🎉 Alle Tests bestanden!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  ❌ Fehlgeschlagen: {', '.join(failed)}")
    print(f"{'='*60}\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
