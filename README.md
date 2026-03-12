# 📊 FinanzBro – Intelligentes Portfolio Dashboard

Echtzeit-Portfolio-Dashboard mit Multi-Faktor-Scoring, automatischem Rebalancing und AI-gestützter Analyse.  
Läuft lokal und auf **Google Cloud Run**.

## Architektur

```
Browser (HTML/JS/CSS)
    ↕ REST API + SSE
FastAPI Backend (lokal / Cloud Run)
    ├── routes/          → API-Endpunkte
    ├── engine/          → Scoring, Analyse, Rebalancing, Analytics
    ├── services/        → Refresh, AI Agent, Telegram, Scheduler
    ├── fetchers/        → Datenquellen (Parqet, FMP, yfinance, Finnhub)
    └── cache/           → Persistente Caches (JSON)
```

## Datenquellen

| Quelle | Modul | Auth | Liefert |
|---|---|---|---|
| **Parqet** | `fetchers/parqet.py` | OAuth2 / JWT | Portfolio-Positionen, Kaufkurse, Sektoren |
| **FMP** | `fetchers/fmp.py` | `FMP_API_KEY` | Fundamentals, Analysten, Dividenden, News, Earnings |
| **yfinance** | `fetchers/yfinance_data.py` | – | Kurse, Historische Daten, Market-Cap, Beta, Indizes |
| **Finnhub** | `fetchers/finnhub_ws.py` | `FINNHUB_API_KEY` | Echtzeit-Kurse (WebSocket, nur US) |
| **CNN** | `fetchers/fear_greed.py` | – | Fear & Greed Index |
| **Currency** | `fetchers/currency.py` | – | EUR/USD, EUR/DKK, EUR/GBP Wechselkurse |

> FMP Free Tier: 250 Requests/Tag. Alle anderen Quellen sind kostenlos.

## Parqet API-Anbindung

Zwei Wege zum gleichen Ergebnis (19 Aktien + 1 Cash = 20 Positionen):

| | Lokal | Cloud Run |
|---|---|---|
| **API** | Internal API (`api.parqet.com`) | Connect API (`connect.parqet.com`) |
| **Auth** | Supabase JWT aus Firefox-Cookies | OAuth2 PKCE Token |
| **Pagination** | Offset (`?limit=100&offset=N`) | Cursor (`?cursor=abc`) |
| **Fallback** | – | Stale Cache + yfinance Preise |

**Setup Cloud Run:** Einmalig `/api/parqet/authorize` aufrufen → Parqet-Login → OAuth2 Tokens gespeichert.

## API-Endpoints

### Portfolio (`routes/portfolio.py`)
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/` | Dashboard (HTML) |
| GET | `/api/portfolio` | Portfolio-Daten (JSON) |
| GET | `/api/stock/{ticker}` | Einzelaktie Details |
| GET | `/api/stock/{ticker}/history` | Kurshistorie |
| GET | `/api/portfolio/history` | Portfolio-Wert-Entwicklung |
| GET | `/api/portfolio/activities` | Transaktionshistorie |
| GET | `/api/rebalancing` | Rebalancing-Empfehlungen |
| GET | `/api/tech-picks` | Tech-Aktien Screening |
| GET | `/api/sectors` | Sektor-Allokation |
| GET | `/api/fear-greed` | Fear & Greed Index |
| GET | `/api/status` | System-Status |

### Refresh (`routes/refresh.py`)
| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/api/refresh` | Kompletter Refresh (alle Datenquellen) |
| POST | `/api/refresh/prices` | Nur Kurse updaten |
| POST | `/api/refresh/portfolio` | Parqet + Kurse |
| POST | `/api/refresh/parqet` | Nur Parqet-Positionen |
| POST | `/api/refresh/scores` | Nur Scores neuberechnen |

### Analyse (`routes/analysis.py`)
| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/api/analysis/run?level=full` | Analyse starten (full/mid/light) |
| GET | `/api/analysis/latest` | Letzter Report |
| GET | `/api/analysis/history` | Report-Historie |
| GET | `/api/analysis/trend/{ticker}` | Score-Trend |

### Analytics (`routes/analytics.py`)
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/api/market-indices` | S&P 500, Nasdaq, DAX Tageswerte |
| GET | `/api/movers` | Top Gewinner/Verlierer |
| GET | `/api/heatmap` | Portfolio-Treemap Daten |
| GET | `/api/dividends` | Dividenden-Übersicht |
| GET | `/api/benchmark?symbol=SPY&period=6month` | Benchmark-Vergleich |
| GET | `/api/correlation` | Korrelationsmatrix |
| GET | `/api/risk` | Beta, VaR, Max Drawdown |
| GET | `/api/earnings-calendar` | Nächste Earnings-Termine |
| GET | `/api/stock/{ticker}/news` | Aktien-News |
| GET | `/api/stock/{ticker}/score-history` | Score-Verlauf |

### OAuth2 (`routes/parqet_oauth.py`)
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/api/parqet/authorize` | OAuth2-Login bei Parqet starten |
| GET | `/api/parqet/callback` | OAuth2-Callback (automatisch) |

### Streaming (`routes/streaming.py`)
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/api/prices/stream` | Server-Sent Events (Echtzeit-Kurse) |

## Scoring Engine (`engine/scorer.py`)

9-Faktor-Bewertungssystem (0–100 Score):

| Faktor | Gewicht | Quelle |
|---|---|---|
| Quality (ROE, Margins, Debt) | 20% | FMP |
| Valuation (P/E, P/B) | 15% | FMP |
| Analyst Consensus + Kursziele | 15% | FMP |
| Technical (RSI, SMA, MACD) | 10% | yfinance |
| Quantitative (FMP Rating) | 5% | FMP |
| Growth (Revenue, Earnings) | 15% | FMP + yfinance |
| ESG Risk | 5% | yfinance |
| Insider Trading | 5% | yfinance |
| Market Sentiment (Fear&Greed) | 10% | CNN |

**Rating:** Buy (≥65), Hold (40–64), Sell (<40)

## Deployment

### Lokal
```bash
python -m venv venv
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

### Cloud Run
```bash
# Über Workflow (empfohlen):
# 1. Tokens aus Firefox extrahieren
# 2. Tests laufen lassen
# 3. Deployen mit frischen Tokens
```

Oder manuell: `gcloud run deploy finanzbro --source . --region europe-west1`

### Environment (.env)
```env
# Pflicht
FMP_API_KEY=...
PARQET_PORTFOLIO_ID=...

# Optional (Erweiterte Features)
FINNHUB_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
GEMINI_API_KEY=...

# Cloud Run (automatisch gesetzt)
ENVIRONMENT=production
GCP_PROJECT_ID=...
PARQET_ACCESS_TOKEN=...
PARQET_REFRESH_TOKEN=...
```

### Scheduler (Cloud Run)

| Job | Zeit | Funktion |
|-----|------|----------|
| Daily Refresh | `06:00` | Voller Daten-Refresh |
| Price Update | alle `30 min` | Quick-Price-Refresh |
| AI Agent | `15:50` | KI-Analyse + Telegram-Report |

### Tests
```bash
python -m pytest tests/ -v    # 223 Tests
```

## Projektstruktur

```
FinanzBro/
├── main.py              # FastAPI App + Startup + Scheduler
├── config.py            # Konfiguration aus .env
├── models.py            # Pydantic-Modelle
├── state.py             # Globaler App-State
├── cache_manager.py     # JSON-basierter Cache
├── Dockerfile           # Cloud Run Container
├── engine/
│   ├── scorer.py        # 9-Faktor Score-Berechnung
│   ├── analysis.py      # Report-Generierung + Score-Historie
│   ├── analytics.py     # Korrelation, Risiko, Dividenden
│   ├── rebalancer.py    # Rebalancing-Empfehlungen
│   └── history.py       # Portfolio-Snapshots
├── fetchers/
│   ├── parqet.py        # Parqet API (Internal + Connect, Cursor/Offset-Pagination)
│   ├── parqet_auth.py   # Token-Management (JWT, Firefox, OAuth2 PKCE)
│   ├── fmp.py           # Financial Modeling Prep
│   ├── yfinance_data.py # Yahoo Finance (Batch-Download)
│   ├── finnhub_ws.py    # Finnhub WebSocket
│   ├── technical.py     # RSI, SMA, MACD
│   ├── fear_greed.py    # CNN Fear & Greed
│   ├── currency.py      # Wechselkurse
│   └── demo_data.py     # Demo-Daten
├── routes/
│   ├── portfolio.py     # Portfolio + Dashboard
│   ├── refresh.py       # Refresh-Endpunkte
│   ├── analysis.py      # Analyse-Report
│   ├── analytics.py     # Erweiterte Analysen
│   ├── parqet_oauth.py  # OAuth2 PKCE (authorize + callback)
│   └── streaming.py     # SSE Preis-Stream
├── services/
│   ├── refresh.py       # Haupt-Refresh-Logic
│   ├── ai_agent.py      # Gemini AI + Telegram Reports
│   ├── telegram.py      # Telegram API
│   ├── currency_converter.py
│   └── scheduler.py     # Geplante Analysen
├── scripts/
│   ├── extract_parqet_tokens.py
│   └── deploy_cloud_run.py
├── static/
│   ├── index.html       # Dashboard UI
│   ├── app.js           # Frontend-Logic
│   └── styles.css       # Styling
└── tests/               # 223 Unit Tests
```
