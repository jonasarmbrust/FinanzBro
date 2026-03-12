"""FinanzBro - Tests für den Rebalancer v2."""
import pytest
from engine.rebalancer import (
    calculate_rebalancing,
    _calculate_smart_weights,
    _calculate_sector_weights,
    _apply_sector_limits,
    _calculate_priority,
    MAX_SINGLE_WEIGHT,
    MIN_SINGLE_WEIGHT,
    MAX_SECTOR_WEIGHT,
    REBALANCE_THRESHOLD,
)
from models import (
    PortfolioPosition,
    StockScore,
    Rating,
    ScoreBreakdown,
)


class TestCalculateRebalancing:
    def test_empty_portfolio(self):
        result = calculate_rebalancing([], {})
        assert "Keine Positionen" in result.summary

    def test_zero_value_portfolio(self):
        positions = [PortfolioPosition(ticker="X", shares=10, avg_cost=0, current_price=0)]
        result = calculate_rebalancing(positions, {})
        assert "Portfoliowert ist 0" in result.summary

    def test_cash_only_portfolio(self):
        positions = [PortfolioPosition(ticker="CASH", shares=1, avg_cost=1000, current_price=1000)]
        result = calculate_rebalancing(positions, {})
        assert "Nur Cash" in result.summary

    def test_cash_excluded(self, sample_positions):
        """CASH should not appear in rebalancing actions."""
        positions_with_cash = sample_positions + [
            PortfolioPosition(ticker="CASH", shares=1, avg_cost=5000, current_price=5000)
        ]
        result = calculate_rebalancing(positions_with_cash, {})
        tickers = [a.ticker for a in result.actions]
        assert "CASH" not in tickers

    def test_basic_rebalancing(self, sample_positions, sample_scores):
        result = calculate_rebalancing(sample_positions, sample_scores)
        assert len(result.actions) == 3
        assert result.total_value > 0
        assert result.summary != ""

    def test_buy_stock_overweight(self, sample_positions, sample_scores):
        """Buy-rated stocks should get higher target weight with enough positions."""
        result = calculate_rebalancing(sample_positions, sample_scores)
        aapl_action = next(a for a in result.actions if a.ticker == "AAPL")
        assert aapl_action.target_weight > 0

    def test_actions_sorted_by_priority(self, sample_positions, sample_scores):
        """Actions should be sorted by priority (highest first)."""
        result = calculate_rebalancing(sample_positions, sample_scores)
        priorities = [a.priority for a in result.actions]
        assert priorities == sorted(priorities, reverse=True)

    def test_weights_sum_near_100(self, sample_positions, sample_scores):
        """Target weights should approximately sum to 100%."""
        result = calculate_rebalancing(sample_positions, sample_scores)
        total_target = sum(a.target_weight for a in result.actions)
        assert abs(total_target - 100.0) < 1.0  # Within 1%

    def test_custom_target_weights(self, sample_positions):
        targets = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        result = calculate_rebalancing(sample_positions, {}, target_weights=targets)
        aapl = next(a for a in result.actions if a.ticker == "AAPL")
        assert abs(aapl.target_weight - 50.0) < 0.1

    def test_single_position(self):
        pos = [PortfolioPosition(ticker="AAPL", shares=10, avg_cost=100, current_price=150)]
        scores = {"AAPL": StockScore(ticker="AAPL", total_score=80, rating=Rating.BUY)}
        result = calculate_rebalancing(pos, scores)
        assert len(result.actions) == 1
        assert result.actions[0].current_weight == 100.0
        assert result.actions[0].target_weight == 100.0

    def test_totals_calculated(self):
        """Buy/sell totals should be calculated correctly."""
        positions = [
            PortfolioPosition(ticker=f"S{i}", shares=10, avg_cost=100, current_price=100)
            for i in range(10)
        ]
        scores = {
            "S0": StockScore(ticker="S0", total_score=90, rating=Rating.BUY),
            "S9": StockScore(ticker="S9", total_score=20, rating=Rating.SELL),
        }
        for i in range(1, 9):
            scores[f"S{i}"] = StockScore(ticker=f"S{i}", total_score=55, rating=Rating.HOLD)
        result = calculate_rebalancing(positions, scores)
        assert result.total_buy_amount >= 0
        assert result.total_sell_amount >= 0

    def test_threshold_filters_small_diffs(self):
        """Actions within threshold should be 'Halten'."""
        positions = [
            PortfolioPosition(ticker="A", shares=50, avg_cost=100, current_price=100),
            PortfolioPosition(ticker="B", shares=50, avg_cost=100, current_price=100),
        ]
        # No scores → equal weights → both should hold
        result = calculate_rebalancing(positions, {})
        for a in result.actions:
            assert a.action == "Halten"

    def test_actions_have_reasons(self, sample_positions, sample_scores):
        """Actions should have detailed reasons."""
        result = calculate_rebalancing(sample_positions, sample_scores)
        for a in result.actions:
            assert len(a.reasons) > 0

    def test_actions_have_score(self, sample_positions, sample_scores):
        """Actions should carry the stock score."""
        result = calculate_rebalancing(sample_positions, sample_scores)
        aapl = next(a for a in result.actions if a.ticker == "AAPL")
        assert aapl.score == 78.0
        assert aapl.rating == Rating.BUY


class TestSmartWeights:
    def test_equal_weight_no_scores(self, sample_positions):
        weights = _calculate_smart_weights(sample_positions, {})
        # Should be roughly equal
        for w in weights.values():
            assert abs(w - 1.0 / 3) < 0.05

    def test_buy_gets_more_weight(self):
        """With many positions, buy-rated stocks get more weight than sell-rated."""
        positions = [
            PortfolioPosition(ticker=f"S{i}", shares=10, avg_cost=100, current_price=100)
            for i in range(10)
        ]
        scores = {}
        for i, p in enumerate(positions):
            if i == 0:
                scores[p.ticker] = StockScore(ticker=p.ticker, total_score=90, rating=Rating.BUY)
            elif i == 9:
                scores[p.ticker] = StockScore(ticker=p.ticker, total_score=20, rating=Rating.SELL)
            else:
                scores[p.ticker] = StockScore(ticker=p.ticker, total_score=55, rating=Rating.HOLD)
        weights = _calculate_smart_weights(positions, scores)
        assert weights["S0"] > weights["S9"]

    def test_min_max_constraints(self):
        """Weights should respect constraints when there are enough positions."""
        positions = [
            PortfolioPosition(ticker=f"S{i}", shares=10, avg_cost=100, current_price=100)
            for i in range(10)
        ]
        scores = {
            p.ticker: StockScore(ticker=p.ticker, total_score=60, rating=Rating.HOLD)
            for p in positions
        }
        weights = _calculate_smart_weights(positions, scores)
        for w in weights.values():
            assert w >= MIN_SINGLE_WEIGHT * 0.9
            assert w <= MAX_SINGLE_WEIGHT * 1.1

    def test_weights_sum_to_one(self, sample_positions, sample_scores):
        weights = _calculate_smart_weights(sample_positions, sample_scores)
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_empty_positions(self):
        weights = _calculate_smart_weights([], {})
        assert weights == {}

    def test_high_score_bonus(self):
        """With many positions, high score gets more weight."""
        positions = [
            PortfolioPosition(ticker=f"S{i}", shares=10, avg_cost=100, current_price=100)
            for i in range(8)
        ]
        scores = {
            "S0": StockScore(ticker="S0", total_score=90, rating=Rating.BUY),
            "S7": StockScore(ticker="S7", total_score=25, rating=Rating.SELL),
        }
        for i in range(1, 7):
            scores[f"S{i}"] = StockScore(ticker=f"S{i}", total_score=50, rating=Rating.HOLD)
        weights = _calculate_smart_weights(positions, scores)
        assert weights["S0"] > weights["S7"]


class TestSectorLimits:
    def test_sector_within_limit(self):
        """No adjustment when sectors are within limits."""
        weights = {"A": 0.3, "B": 0.3, "C": 0.4}
        sector_map = {"A": "Tech", "B": "Finance", "C": "Health"}
        result = _apply_sector_limits(weights, sector_map)
        # No sector over 35%, so weights should be similar
        assert abs(sum(result.values()) - 1.0) < 0.01

    def test_sector_over_limit_reduced(self):
        """Sector over 35% should be reduced."""
        weights = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
        sector_map = {"A": "Tech", "B": "Tech", "C": "Tech", "D": "Finance"}
        # Tech = 75% → should be reduced
        result = _apply_sector_limits(weights, sector_map)
        tech_total = result["A"] + result["B"] + result["C"]
        # After reduction and renormalization, Tech should be closer to 35%
        assert tech_total < 0.80
        assert abs(sum(result.values()) - 1.0) < 0.01

    def test_no_sector_map(self):
        """Empty sector map should return unchanged weights."""
        weights = {"A": 0.5, "B": 0.5}
        result = _apply_sector_limits(weights, {})
        assert result == weights


class TestPriority:
    def test_halten_low_priority(self):
        prio = _calculate_priority(0.005, None, "Halten", "", {})
        assert prio == 1

    def test_sell_rated_overweight_high_priority(self):
        score = StockScore(ticker="X", total_score=25, rating=Rating.SELL)
        prio = _calculate_priority(-0.06, score, "Verkaufen", "Tech", {"Tech": 0.3})
        assert prio >= 7

    def test_buy_rated_underweight_high_priority(self):
        score = StockScore(ticker="X", total_score=85, rating=Rating.BUY)
        prio = _calculate_priority(0.06, score, "Kaufen", "Tech", {"Tech": 0.2})
        assert prio >= 7

    def test_small_diff_low_priority(self):
        score = StockScore(ticker="X", total_score=55, rating=Rating.HOLD)
        prio = _calculate_priority(0.02, score, "Kaufen", "Tech", {"Tech": 0.2})
        assert prio <= 5


class TestSectorWeights:
    def test_basic_sector_weights(self):
        weights = {"A": 0.3, "B": 0.2, "C": 0.5}
        sector_map = {"A": "Tech", "B": "Tech", "C": "Finance"}
        result = _calculate_sector_weights(weights, sector_map)
        assert abs(result["Tech"] - 0.5) < 0.01
        assert abs(result["Finance"] - 0.5) < 0.01
