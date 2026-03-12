"""FinanzBro - AI Trade Advisor Tests."""
import pytest
from unittest.mock import patch, MagicMock

from services.trade_advisor import (
    _build_portfolio_context,
    _build_advisor_prompt,
    _parse_ai_response,
)


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

class MockPosition:
    def __init__(self, ticker, name="", sector="", current_value=1000, current_price=100,
                 total_cost=900, pnl_percent=11.1, daily_change_pct=None):
        self.ticker = ticker
        self.name = name
        self.sector = sector
        self.current_value = current_value
        self.current_price = current_price
        self.total_cost = total_cost
        self.pnl_percent = pnl_percent
        self.daily_change_pct = daily_change_pct


class MockScore:
    def __init__(self, total_score=75.0, rating_value="buy", confidence=0.8):
        self.total_score = total_score
        self.confidence = confidence

        class _Rating:
            def __init__(self, v):
                self.value = v
        self.rating = _Rating(rating_value)

        class _Breakdown:
            quality_score = 70
            valuation_score = 65
            analyst_score = 80
            technical_score = 60
            momentum_score = 55
            sentiment_score = 50
        self.breakdown = _Breakdown()


class MockStock:
    def __init__(self, ticker, name="", sector="Tech", value=1000, score_val=75):
        self.position = MockPosition(ticker, name, sector, current_value=value)
        self.score = MockScore(score_val) if score_val else None


class MockSummary:
    def __init__(self):
        self.total_value = 10000
        self.total_pnl_percent = 15.5
        self.num_positions = 3
        self.stocks = [
            MockStock("AAPL", "Apple", "Technology", 4000, 78),
            MockStock("MSFT", "Microsoft", "Technology", 3000, 72),
            MockStock("JNJ", "Johnson & Johnson", "Healthcare", 3000, 65),
        ]

        class _FG:
            value = 55
            label = "Greed"
        self.fear_greed = _FG()


# ─────────────────────────────────────────────────────────────
# Tests: Portfolio Context
# ─────────────────────────────────────────────────────────────

class TestBuildPortfolioContext:
    def test_builds_sector_distribution(self):
        summary = MockSummary()
        ctx = _build_portfolio_context(summary, "NVDA", "buy", 2000)

        assert "Technology" in ctx["sector_distribution"]
        assert "Healthcare" in ctx["sector_distribution"]
        assert ctx["total_value"] == 10000
        assert ctx["num_positions"] == 3

    def test_includes_fear_greed(self):
        summary = MockSummary()
        ctx = _build_portfolio_context(summary, "NVDA", "buy", None)

        assert ctx["fear_greed"] == 55
        assert ctx["fear_greed_label"] == "Greed"

    def test_top_positions_ordered_by_weight(self):
        summary = MockSummary()
        ctx = _build_portfolio_context(summary, "NVDA", "buy", None)

        assert len(ctx["top_positions"]) == 3
        assert ctx["top_positions"][0]["ticker"] == "AAPL"  # Highest value


# ─────────────────────────────────────────────────────────────
# Tests: Prompt Builder
# ─────────────────────────────────────────────────────────────

class TestBuildAdvisorPrompt:
    def test_includes_ticker_and_action(self):
        prompt = _build_advisor_prompt(
            ticker="NVDA", action="buy", amount_eur=2000,
            score_info={"total_score": 75, "rating": "buy", "confidence": 0.8, "breakdown": {}},
            portfolio_ctx={"total_value": 10000, "num_positions": 3, "total_pnl_pct": 15,
                           "sector_distribution": {}, "top_positions": [], "impact": {}},
            extra_context=None,
        )

        assert "NVDA" in prompt
        assert "KAUF" in prompt
        assert "2.000 EUR" in prompt or "2,000 EUR" in prompt

    def test_includes_external_context(self):
        prompt = _build_advisor_prompt(
            ticker="NVDA", action="buy", amount_eur=None,
            score_info={"total_score": None, "rating": "unknown", "confidence": 0},
            portfolio_ctx={"total_value": 10000, "num_positions": 3, "total_pnl_pct": 15,
                           "sector_distribution": {}, "top_positions": [], "impact": {}},
            extra_context="Goldman Sachs hat NVDA auf Buy hochgestuft",
        )

        assert "Goldman Sachs" in prompt
        assert "EXTERNE QUELLEN" in prompt

    def test_prompt_requests_json(self):
        prompt = _build_advisor_prompt(
            ticker="AAPL", action="sell", amount_eur=None,
            score_info={"total_score": 40, "rating": "sell", "confidence": 0.6, "breakdown": {}},
            portfolio_ctx={"total_value": 10000, "num_positions": 3, "total_pnl_pct": 15,
                           "sector_distribution": {}, "top_positions": [], "impact": {}},
            extra_context=None,
        )

        assert "JSON" in prompt
        assert '"recommendation"' in prompt


# ─────────────────────────────────────────────────────────────
# Tests: Response Parsing
# ─────────────────────────────────────────────────────────────

class TestParseAiResponse:
    def test_parses_valid_json(self):
        raw = '{"recommendation": "buy", "confidence": 85, "summary": "Gutes Investment"}'
        result = _parse_ai_response(raw)

        assert result["recommendation"] == "buy"
        assert result["confidence"] == 85
        assert result["summary"] == "Gutes Investment"

    def test_strips_markdown_code_block(self):
        raw = '```json\n{"recommendation": "hold", "confidence": 60}\n```'
        result = _parse_ai_response(raw)

        assert result["recommendation"] == "hold"
        assert result["confidence"] == 60

    def test_fills_defaults_for_missing_fields(self):
        raw = '{"recommendation": "buy"}'
        result = _parse_ai_response(raw)

        assert result["recommendation"] == "buy"
        assert "risks" in result
        assert isinstance(result["risks"], list)
        assert "bull_case" in result

    def test_handles_invalid_json(self):
        raw = "Dies ist kein JSON sondern ein normaler Text"
        result = _parse_ai_response(raw)

        assert result["recommendation"] == "hold"
        assert raw[:100] in result.get("summary", "") or "raw_response" in result

    def test_handles_empty_response(self):
        result = _parse_ai_response("")

        assert result["recommendation"] == "hold"


class TestEvaluateTradeNoGemini:
    @pytest.mark.asyncio
    async def test_without_gemini_returns_error(self):
        with patch("services.trade_advisor.settings") as mock_settings:
            mock_settings.gemini_configured = False
            from services.trade_advisor import evaluate_trade
            result = await evaluate_trade("NVDA", "buy")

            assert "error" in result
            assert "Gemini" in result["error"]
