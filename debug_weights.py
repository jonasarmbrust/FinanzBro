import json
from engine.rebalancer import calculate_rebalancing
from models import PortfolioPosition, StockScore, Rating, ScoreBreakdown

positions = [
    PortfolioPosition(ticker="NOVO-B.CO", name="Novo Nordisk", shares=100, avg_cost=100, current_price=120, sector="Healthcare"),
    PortfolioPosition(ticker="GOOGL", name="Alphabet", shares=20, avg_cost=110, current_price=150, sector="Communication Services"),
    PortfolioPosition(ticker="AAPL", name="Apple", shares=30, avg_cost=150, current_price=170, sector="Technology"),
]

# Simulate a situation where NOVO has a GOOD score but is a small part of portfolio
# and GOOGL has a OK score but is a huge part of portfolio (overweight)
scores = {
    "NOVO-B.CO": StockScore(ticker="NOVO-B.CO", total_score=85, rating=Rating.BUY, breakdown=ScoreBreakdown()),
    "GOOGL": StockScore(ticker="GOOGL", total_score=60, rating=Rating.HOLD, breakdown=ScoreBreakdown()),
    "AAPL": StockScore(ticker="AAPL", total_score=75, rating=Rating.BUY, breakdown=ScoreBreakdown()),
}

res = calculate_rebalancing(positions, scores)

print("\n--- TEST REBALANCING ---")
for a in res.actions:
    print(f"{a.ticker}: {a.action} (Cur: {a.current_weight}%, Tgt: {a.target_weight}%) - Score: {a.score}")
    for r in a.reasons:
        print(f"  - {r}")
