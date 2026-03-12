# FinanzBro – Scoring Engine v4

## Übersicht

9-Faktor Multi-Analyse-System mit sektorbasierter Bewertung.
Jeder Faktor wird auf 0-100 normalisiert, gewichtet zusammengeführt.

## Faktoren & Gewichte

| # | Faktor | Gewicht | Datenquelle | Beschreibung |
|---|--------|---------|-------------|--------------|
| 1 | **Quality** | 20% | FMP/yFinance | ROE, Gross Margin, Operating Margin, D/E, Current Ratio |
| 2 | **Valuation** | 15% | FMP | P/E, EV/EBITDA, PEG, FCF Yield — **sektorbasiert** |
| 3 | **Analyst** | 15% | FMP/yFinance | Konsens (60%) + Preisziel (40%), merged |
| 4 | **Technical** | 15% | yFinance | RSI-14, SMA Cross, Momentum 30d, Price vs SMA50 |
| 5 | **Growth** | 12% | FMP + yFinance | Revenue Growth, Earnings Growth YoY, ROIC |
| 6 | **Quantitative** | 10% | FMP | Altman Z-Score, Piotroski Score |
| 7 | **Sentiment** | 8% | CNN | Fear & Greed Index (Markt-Level) |
| 8 | **Insider** | 3% | yFinance | Insider Buy/Sell Ratio |
| 9 | **ESG** | 2% | yFinance | ESG Risk Score |

**Summe Gewichte: 100%**

## Dynamische Gewichtung

Faktoren ohne verfügbare Daten werden ausgeblendet. Die übrigen werden
proportional hochskaliert, damit die Summe immer 100% beträgt.

## Sektorbasierte Valuation

Nicht jeder Sektor wird gleich bewertet. Ein P/E von 30 ist für Tech-Aktien normal,
für Financials wäre es teuer:

| Sektor | P/E Fair | P/E Günstig | P/E Teuer |
|--------|----------|-------------|-----------|
| Technology | 30 | 20 | 45 |
| Financials | 14 | 10 | 22 |
| Healthcare | 22 | 14 | 35 |
| Energy | 12 | 8 | 20 |
| Consumer Defensive | 20 | 14 | 30 |
| Default | 20 | 14 | 35 |

## Schwellenwerte

| Rating | Score |
|--------|-------|
| 🟢 **BUY** | ≥ 68 |
| 🟡 **HOLD** | 40 – 67 |
| 🔴 **SELL** | < 40 |

## Confidence

Basiert auf der Anzahl verfügbarer Faktoren:
- 9/9 Faktoren → Confidence 1.0
- 5/9 Faktoren → Confidence 0.56
- 0 Faktoren → Confidence 0.0, automatisch HOLD mit Score 50

## v4 Änderungen (gegenüber v3)

- ~~FMP Rating~~ entfernt (Black Box, duplizierte eigene Checks)
- ~~AlphaVantage~~ entfernt (Sentiment nur noch Fear&Greed)
- Preisziel in Analyst-Score **gemerged** (60/40 Konsens/Preisziel)
- Unit-Normalisierung: 0.25 und 25 → beide als 25%
- Net Margin nur noch in **Quality** (nicht mehr doppelt in Growth)
- Echtes **Earnings Growth YoY** aus yFinance statt netIncomePerShare
