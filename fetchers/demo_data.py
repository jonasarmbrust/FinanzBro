"""FinanzBro - Demo-Daten

Stellt ein Demo-Portfolio mit realistischen Daten bereit,
wenn keine API-Keys konfiguriert sind oder Parqet nicht erreichbar ist.
"""
from models import (
    AnalystData,
    FearGreedData,
    FmpRating,
    FundamentalData,
    PortfolioPosition,
    TechRecommendation,
    YFinanceData,
)


def get_demo_positions() -> list[PortfolioPosition]:
    """Demo-Portfolio mit populären Tech- und Blue-Chip-Aktien."""
    return [
        PortfolioPosition(ticker="AAPL", isin="US0378331005", name="Apple Inc.", shares=15, avg_cost=142.50, current_price=178.72, currency="USD", sector="Technology"),
        PortfolioPosition(ticker="MSFT", isin="US5949181045", name="Microsoft Corp.", shares=10, avg_cost=285.00, current_price=415.30, currency="USD", sector="Technology"),
        PortfolioPosition(ticker="NVDA", isin="US67066G1040", name="NVIDIA Corp.", shares=8, avg_cost=450.00, current_price=875.40, currency="USD", sector="Technology"),
        PortfolioPosition(ticker="GOOGL", isin="US02079K3059", name="Alphabet Inc.", shares=12, avg_cost=105.00, current_price=167.85, currency="USD", sector="Technology"),
        PortfolioPosition(ticker="AMZN", isin="US0231351067", name="Amazon.com Inc.", shares=20, avg_cost=128.00, current_price=195.60, currency="USD", sector="Consumer Cyclical"),
        PortfolioPosition(ticker="META", isin="US30303M1027", name="Meta Platforms Inc.", shares=6, avg_cost=280.00, current_price=505.75, currency="USD", sector="Technology"),
        PortfolioPosition(ticker="TSLA", isin="US88160R1014", name="Tesla Inc.", shares=5, avg_cost=195.00, current_price=178.50, currency="USD", sector="Consumer Cyclical"),
        PortfolioPosition(ticker="ASML", isin="NL0010273215", name="ASML Holding N.V.", shares=3, avg_cost=620.00, current_price=910.25, currency="EUR", sector="Technology"),
        PortfolioPosition(ticker="SAP", isin="DE0007164600", name="SAP SE", shares=25, avg_cost=125.00, current_price=198.40, currency="EUR", sector="Technology"),
        PortfolioPosition(ticker="AVGO", isin="US11135F1012", name="Broadcom Inc.", shares=4, avg_cost=850.00, current_price=1680.50, currency="USD", sector="Technology"),
        PortfolioPosition(ticker="CRM", isin="US79466L3024", name="Salesforce Inc.", shares=8, avg_cost=210.00, current_price=312.40, currency="USD", sector="Technology"),
        PortfolioPosition(ticker="AMD", isin="US0079031078", name="AMD Inc.", shares=15, avg_cost=95.00, current_price=168.75, currency="USD", sector="Technology"),
    ]


def get_demo_fundamentals() -> dict[str, FundamentalData]:
    """Demo-Fundamentaldaten (inkl. Altman Z-Score & Piotroski)."""
    return {
        "AAPL": FundamentalData(pe_ratio=28.5, pb_ratio=45.2, roe=1.56, debt_to_equity=1.87, current_ratio=0.98, gross_margin=0.462, operating_margin=0.304, net_margin=0.261, market_cap=2750000000000, beta=1.21, dividend_yield=0.005, altman_z_score=5.2, piotroski_score=7),
        "MSFT": FundamentalData(pe_ratio=35.2, pb_ratio=12.8, roe=0.39, debt_to_equity=0.42, current_ratio=1.77, gross_margin=0.705, operating_margin=0.445, net_margin=0.362, market_cap=3080000000000, beta=0.89, dividend_yield=0.007, altman_z_score=8.1, piotroski_score=8),
        "NVDA": FundamentalData(pe_ratio=65.4, pb_ratio=52.3, roe=1.15, debt_to_equity=0.41, current_ratio=4.17, gross_margin=0.760, operating_margin=0.620, net_margin=0.553, market_cap=2150000000000, beta=1.68, altman_z_score=12.5, piotroski_score=8),
        "GOOGL": FundamentalData(pe_ratio=24.1, pb_ratio=6.8, roe=0.28, debt_to_equity=0.10, current_ratio=2.10, gross_margin=0.574, operating_margin=0.321, net_margin=0.257, market_cap=2080000000000, beta=1.05, altman_z_score=9.8, piotroski_score=7),
        "AMZN": FundamentalData(pe_ratio=58.3, pb_ratio=8.9, roe=0.21, debt_to_equity=0.56, current_ratio=1.05, gross_margin=0.478, operating_margin=0.076, net_margin=0.062, market_cap=2020000000000, beta=1.15, altman_z_score=4.2, piotroski_score=6),
        "META": FundamentalData(pe_ratio=25.8, pb_ratio=8.2, roe=0.30, debt_to_equity=0.32, current_ratio=2.68, gross_margin=0.810, operating_margin=0.406, net_margin=0.356, market_cap=1290000000000, beta=1.24, altman_z_score=7.6, piotroski_score=7),
        "TSLA": FundamentalData(pe_ratio=48.7, pb_ratio=11.5, roe=0.21, debt_to_equity=0.11, current_ratio=1.73, gross_margin=0.182, operating_margin=0.087, net_margin=0.078, market_cap=568000000000, beta=2.05, altman_z_score=3.1, piotroski_score=4),
        "ASML": FundamentalData(pe_ratio=42.3, pb_ratio=22.1, roe=0.76, debt_to_equity=0.44, current_ratio=1.45, gross_margin=0.512, operating_margin=0.365, net_margin=0.282, market_cap=362000000000, beta=1.15, altman_z_score=6.8, piotroski_score=7),
        "SAP": FundamentalData(pe_ratio=38.5, pb_ratio=5.8, roe=0.15, debt_to_equity=0.48, current_ratio=1.12, gross_margin=0.725, operating_margin=0.288, net_margin=0.168, market_cap=243000000000, beta=0.95, dividend_yield=0.011, altman_z_score=5.5, piotroski_score=6),
        "AVGO": FundamentalData(pe_ratio=35.8, pb_ratio=11.2, roe=0.42, debt_to_equity=1.64, current_ratio=1.10, gross_margin=0.740, operating_margin=0.465, net_margin=0.392, market_cap=780000000000, beta=1.18, dividend_yield=0.012, altman_z_score=4.8, piotroski_score=7),
        "CRM": FundamentalData(pe_ratio=52.1, pb_ratio=4.5, roe=0.08, debt_to_equity=0.20, current_ratio=1.02, gross_margin=0.755, operating_margin=0.218, net_margin=0.148, market_cap=303000000000, beta=1.12, altman_z_score=5.9, piotroski_score=5),
        "AMD": FundamentalData(pe_ratio=42.8, pb_ratio=4.2, roe=0.04, debt_to_equity=0.04, current_ratio=2.51, gross_margin=0.498, operating_margin=0.235, net_margin=0.052, market_cap=272000000000, beta=1.72, altman_z_score=8.3, piotroski_score=6),
    }


def get_demo_analyst_data() -> dict[str, AnalystData]:
    """Demo-Analysten-Daten (inkl. Strong Buy/Sell)."""
    return {
        "AAPL": AnalystData(consensus="Buy", target_price=200.00, num_analysts=42, strong_buy_count=12, buy_count=18, hold_count=10, sell_count=1, strong_sell_count=1),
        "MSFT": AnalystData(consensus="Buy", target_price=470.00, num_analysts=48, strong_buy_count=20, buy_count=20, hold_count=7, sell_count=1, strong_sell_count=0),
        "NVDA": AnalystData(consensus="Buy", target_price=1050.00, num_analysts=52, strong_buy_count=28, buy_count=18, hold_count=5, sell_count=1, strong_sell_count=0),
        "GOOGL": AnalystData(consensus="Buy", target_price=195.00, num_analysts=45, strong_buy_count=18, buy_count=20, hold_count=6, sell_count=1, strong_sell_count=0),
        "AMZN": AnalystData(consensus="Buy", target_price=225.00, num_analysts=50, strong_buy_count=22, buy_count=20, hold_count=6, sell_count=1, strong_sell_count=1),
        "META": AnalystData(consensus="Buy", target_price=575.00, num_analysts=44, strong_buy_count=18, buy_count=20, hold_count=5, sell_count=1, strong_sell_count=0),
        "TSLA": AnalystData(consensus="Hold", target_price=195.00, num_analysts=40, strong_buy_count=3, buy_count=9, hold_count=18, sell_count=7, strong_sell_count=3),
        "ASML": AnalystData(consensus="Buy", target_price=1050.00, num_analysts=28, strong_buy_count=10, buy_count=12, hold_count=5, sell_count=1, strong_sell_count=0),
        "SAP": AnalystData(consensus="Buy", target_price=225.00, num_analysts=32, strong_buy_count=10, buy_count=14, hold_count=7, sell_count=1, strong_sell_count=0),
        "AVGO": AnalystData(consensus="Buy", target_price=1900.00, num_analysts=30, strong_buy_count=14, buy_count=12, hold_count=3, sell_count=1, strong_sell_count=0),
        "CRM": AnalystData(consensus="Hold", target_price=340.00, num_analysts=38, strong_buy_count=6, buy_count=12, hold_count=16, sell_count=3, strong_sell_count=1),
        "AMD": AnalystData(consensus="Buy", target_price=200.00, num_analysts=42, strong_buy_count=14, buy_count=18, hold_count=8, sell_count=2, strong_sell_count=0),
    }


def get_demo_fmp_ratings() -> dict[str, FmpRating]:
    """Demo-FMP Ratings."""
    return {
        "AAPL": FmpRating(rating="A", rating_score=4, dcf_score=4, roe_score=5, roa_score=4, de_score=3, pe_score=4, pb_score=3),
        "MSFT": FmpRating(rating="A+", rating_score=5, dcf_score=4, roe_score=4, roa_score=4, de_score=5, pe_score=4, pb_score=4),
        "NVDA": FmpRating(rating="A", rating_score=4, dcf_score=3, roe_score=5, roa_score=5, de_score=5, pe_score=2, pb_score=2),
        "GOOGL": FmpRating(rating="A+", rating_score=5, dcf_score=5, roe_score=4, roa_score=4, de_score=5, pe_score=5, pb_score=4),
        "AMZN": FmpRating(rating="B+", rating_score=3, dcf_score=3, roe_score=3, roa_score=3, de_score=4, pe_score=2, pb_score=3),
        "META": FmpRating(rating="A", rating_score=4, dcf_score=4, roe_score=4, roa_score=4, de_score=5, pe_score=4, pb_score=4),
        "TSLA": FmpRating(rating="C+", rating_score=2, dcf_score=2, roe_score=3, roa_score=2, de_score=5, pe_score=2, pb_score=2),
        "ASML": FmpRating(rating="A-", rating_score=4, dcf_score=3, roe_score=5, roa_score=4, de_score=4, pe_score=3, pb_score=3),
        "SAP": FmpRating(rating="B+", rating_score=3, dcf_score=3, roe_score=3, roa_score=3, de_score=4, pe_score=3, pb_score=4),
        "AVGO": FmpRating(rating="A-", rating_score=4, dcf_score=4, roe_score=4, roa_score=4, de_score=3, pe_score=4, pb_score=3),
        "CRM": FmpRating(rating="B", rating_score=3, dcf_score=3, roe_score=2, roa_score=3, de_score=5, pe_score=2, pb_score=4),
        "AMD": FmpRating(rating="B+", rating_score=3, dcf_score=3, roe_score=2, roa_score=2, de_score=5, pe_score=3, pb_score=4),
    }




def get_demo_tech_picks() -> list[TechRecommendation]:
    """Demo Tech-Empfehlungen (Tech-Radar v2)."""
    return [
        TechRecommendation(ticker="PLTR", name="Palantir Technologies", current_price=24.50, market_cap=54000000000, pe_ratio=62.5, analyst_rating="Buy", target_price=30.00, upside_percent=22.4, ai_score=8.2, score=82.0, reason="ROE 28% | Revenue +25% | Marge 62% | Konsens: Buy | Upside: 22.4%", tags=["AI", "Software", "Data"], ai_summary="KI-Leader im Government & Enterprise – starkes AIP-Wachstum treibt Profitabilität", revenue_growth=25.0, roe=28.0),
        TechRecommendation(ticker="CRWD", name="CrowdStrike Holdings", current_price=315.00, market_cap=75000000000, pe_ratio=85.0, analyst_rating="Buy", target_price=380.00, upside_percent=20.6, ai_score=7.8, score=78.0, reason="ROE 18% | Revenue +33% | Marge 75% | Konsens: Buy | Upside: 20.6%", tags=["Tech", "Cybersecurity", "Cloud"], ai_summary="Cybersecurity-Marktführer mit XDR-Plattform – Recovery nach Vorjahres-Incident läuft", revenue_growth=33.0, roe=18.0),
        TechRecommendation(ticker="SNOW", name="Snowflake Inc.", current_price=168.00, market_cap=55000000000, pe_ratio=None, analyst_rating="Buy", target_price=210.00, upside_percent=25.0, ai_score=7.5, score=75.0, reason="Revenue +30% | Marge 68% | Konsens: Buy | Upside: 25.0%", tags=["Tech", "Cloud", "Data", "AI"], ai_summary="Cloud-Data-Platform mit AI-Workloads – starkes Kundenwachstum, aber noch nicht profitabel", revenue_growth=30.0, roe=None),
        TechRecommendation(ticker="PANW", name="Palo Alto Networks", current_price=310.00, market_cap=98000000000, pe_ratio=48.0, analyst_rating="Buy", target_price=365.00, upside_percent=17.7, ai_score=7.9, score=79.0, reason="ROE 22% | Revenue +20% | Marge 72% | Konsens: Buy | Upside: 17.7%", tags=["Tech", "Cybersecurity", "Cloud"], ai_summary="Plattform-Konsolidierung zahlt sich aus – SASE & Cortex XSIAM wachsen zweistellig", revenue_growth=20.0, roe=22.0),
        TechRecommendation(ticker="MDB", name="MongoDB Inc.", current_price=365.00, market_cap=26000000000, pe_ratio=None, analyst_rating="Buy", target_price=440.00, upside_percent=20.5, ai_score=7.2, score=72.0, reason="Revenue +22% | Marge 71% | Konsens: Buy | Upside: 20.5%", tags=["Tech", "Cloud", "Data"], ai_summary="Führende NoSQL-Datenbank – AI-Workloads und Atlas-Cloud treiben Wachstum", revenue_growth=22.0, roe=None),
    ]


def get_demo_yfinance_data() -> dict[str, YFinanceData]:
    """Demo-YFinance-Daten (Insider, ESG, Recommendations)."""
    return {
        "AAPL": YFinanceData(recommendation_trend="Buy", insider_buy_count=3, insider_sell_count=8, esg_risk_score=16.7, earnings_growth_yoy=8.5),
        "MSFT": YFinanceData(recommendation_trend="Buy", insider_buy_count=5, insider_sell_count=4, esg_risk_score=14.2, earnings_growth_yoy=18.3),
        "NVDA": YFinanceData(recommendation_trend="Buy", insider_buy_count=2, insider_sell_count=12, esg_risk_score=12.8, earnings_growth_yoy=265.0),
        "GOOGL": YFinanceData(recommendation_trend="Buy", insider_buy_count=4, insider_sell_count=6, esg_risk_score=18.5, earnings_growth_yoy=42.1),
        "AMZN": YFinanceData(recommendation_trend="Buy", insider_buy_count=1, insider_sell_count=15, esg_risk_score=28.4, earnings_growth_yoy=155.0),
        "META": YFinanceData(recommendation_trend="Buy", insider_buy_count=0, insider_sell_count=10, esg_risk_score=24.3, earnings_growth_yoy=73.2),
        "TSLA": YFinanceData(recommendation_trend="Hold", insider_buy_count=1, insider_sell_count=18, esg_risk_score=32.5, earnings_growth_yoy=-23.4),
        "ASML": YFinanceData(recommendation_trend="Buy", insider_buy_count=3, insider_sell_count=2, esg_risk_score=11.5, earnings_growth_yoy=12.8),
        "SAP": YFinanceData(recommendation_trend="Buy", insider_buy_count=6, insider_sell_count=3, esg_risk_score=8.9, earnings_growth_yoy=21.5),
        "AVGO": YFinanceData(recommendation_trend="Buy", insider_buy_count=2, insider_sell_count=5, esg_risk_score=15.3, earnings_growth_yoy=44.8),
        "CRM": YFinanceData(recommendation_trend="Hold", insider_buy_count=2, insider_sell_count=7, esg_risk_score=19.8, earnings_growth_yoy=35.2),
        "AMD": YFinanceData(recommendation_trend="Buy", insider_buy_count=4, insider_sell_count=3, esg_risk_score=13.6, earnings_growth_yoy=62.0),
    }




def get_demo_fear_greed() -> FearGreedData:
    """Demo Fear & Greed Index."""
    return FearGreedData(value=62, label="Greed", source="Demo")


def get_demo_technical_indicators() -> dict[str, "TechnicalIndicators"]:
    """Demo-Technische Indikatoren für alle Demo-Positionen."""
    from models import TechnicalIndicators
    return {
        "AAPL": TechnicalIndicators(rsi_14=58.3, sma_50=172.40, sma_200=165.80, price_vs_sma50=3.7, sma_cross="golden", momentum_30d=4.2, momentum_90d=8.5, momentum_180d=12.1, signal="Bullish"),
        "MSFT": TechnicalIndicators(rsi_14=62.1, sma_50=405.20, sma_200=378.50, price_vs_sma50=2.5, sma_cross="golden", momentum_30d=3.8, momentum_90d=10.2, momentum_180d=15.3, signal="Bullish"),
        "NVDA": TechnicalIndicators(rsi_14=71.5, sma_50=820.00, sma_200=650.00, price_vs_sma50=6.8, sma_cross="golden", momentum_30d=8.5, momentum_90d=25.4, momentum_180d=45.2, signal="Bullish"),
        "GOOGL": TechnicalIndicators(rsi_14=55.8, sma_50=162.30, sma_200=148.70, price_vs_sma50=3.4, sma_cross="golden", momentum_30d=2.1, momentum_90d=7.8, momentum_180d=14.5, signal="Bullish"),
        "AMZN": TechnicalIndicators(rsi_14=60.4, sma_50=188.50, sma_200=172.30, price_vs_sma50=3.8, sma_cross="golden", momentum_30d=5.2, momentum_90d=12.3, momentum_180d=18.7, signal="Bullish"),
        "META": TechnicalIndicators(rsi_14=64.7, sma_50=485.00, sma_200=420.50, price_vs_sma50=4.3, sma_cross="golden", momentum_30d=6.1, momentum_90d=15.8, momentum_180d=28.4, signal="Bullish"),
        "TSLA": TechnicalIndicators(rsi_14=42.3, sma_50=195.80, sma_200=210.50, price_vs_sma50=-8.8, sma_cross="death", momentum_30d=-5.2, momentum_90d=-12.1, momentum_180d=-8.5, signal="Bearish"),
        "ASML": TechnicalIndicators(rsi_14=57.2, sma_50=880.00, sma_200=820.00, price_vs_sma50=3.4, sma_cross="golden", momentum_30d=3.5, momentum_90d=9.2, momentum_180d=16.8, signal="Bullish"),
        "SAP": TechnicalIndicators(rsi_14=61.8, sma_50=190.20, sma_200=172.50, price_vs_sma50=4.3, sma_cross="golden", momentum_30d=4.8, momentum_90d=11.5, momentum_180d=20.3, signal="Bullish"),
        "AVGO": TechnicalIndicators(rsi_14=66.5, sma_50=1580.00, sma_200=1350.00, price_vs_sma50=6.4, sma_cross="golden", momentum_30d=7.2, momentum_90d=18.5, momentum_180d=32.1, signal="Bullish"),
        "CRM": TechnicalIndicators(rsi_14=48.5, sma_50=305.00, sma_200=280.00, price_vs_sma50=2.4, sma_cross="golden", momentum_30d=1.5, momentum_90d=5.8, momentum_180d=10.2, signal="Neutral"),
        "AMD": TechnicalIndicators(rsi_14=53.2, sma_50=158.00, sma_200=142.50, price_vs_sma50=6.8, sma_cross="golden", momentum_30d=3.2, momentum_90d=14.5, momentum_180d=22.8, signal="Bullish"),
    }


def get_demo_portfolio_history(days: int = 180) -> list[dict]:
    """Generiert synthetische Portfolio-Verlaufsdaten für den Demo-Modus.

    Simuliert ein realistisch wachsendes Portfolio mit:
    - Steigendem investiertem Kapital (monatliche Einzahlungen)
    - Marktschwankungen (±2% täglich)
    - Insgesamt positivem Trend
    """
    import random
    from datetime import datetime, timedelta

    random.seed(42)  # Reproduzierbar
    data = []
    invested = 18000.0  # Startwert investiertes Kapital
    value = 20500.0     # Startwert Portfoliowert

    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d")

        # Monatliche Einzahlung (~1500 EUR)
        if i > 0 and i % 30 == 0:
            invested += random.uniform(1200, 1800)

        # Tägliche Marktschwankung
        daily_return = random.gauss(0.0004, 0.012)  # Leicht positiver Bias
        value = value * (1 + daily_return)

        # Invested wächst langsamer als der Wert
        data.append({
            "date": date,
            "total_value": round(value, 2),
            "invested_capital": round(invested, 2),
        })

    return data

