"""FinanzBro - Zentrale Konfiguration"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Lade .env Datei
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """App-Konfiguration aus Environment-Variablen."""

    # Financial Modeling Prep
    FMP_API_KEY: str = os.getenv("FMP_API_KEY", "")
    FMP_BASE_URL: str = "https://financialmodelingprep.com/stable"

    # Finnhub (Echtzeit-Kurse via WebSocket)
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")

    # Parqet Connect API (OAuth2)
    PARQET_CLIENT_ID: str = os.getenv("PARQET_CLIENT_ID", "")
    PARQET_CLIENT_SECRET: str = os.getenv("PARQET_CLIENT_SECRET", "")
    PARQET_ACCESS_TOKEN: str = os.getenv("PARQET_ACCESS_TOKEN", "")
    PARQET_REFRESH_TOKEN: str = os.getenv("PARQET_REFRESH_TOKEN", "")
    PARQET_PORTFOLIO_ID: str = os.getenv("PARQET_PORTFOLIO_ID", "")
    PARQET_API_BASE_URL: str = "https://connect.parqet.com"

    # Parqet CSV Fallback
    PARQET_PORTFOLIO_CSV: str = os.getenv("PARQET_PORTFOLIO_CSV", "portfolio.csv")

    @property
    def parqet_api_configured(self) -> bool:
        """True wenn Parqet API-Zugang konfiguriert ist.

        Akzeptiert sowohl Access-Token als auch Refresh-Token,
        damit auf Cloud Run der Supabase-Refresh funktioniert.
        """
        has_token = bool(self.PARQET_ACCESS_TOKEN or self.PARQET_REFRESH_TOKEN)
        return bool(has_token and self.PARQET_PORTFOLIO_ID)

    # Server
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("PORT", os.getenv("SERVER_PORT", "8000")))

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Scheduler
    DAILY_REFRESH_TIME: str = os.getenv("DAILY_REFRESH_TIME", "06:00")
    PRICE_UPDATE_INTERVAL_MIN: int = int(os.getenv("PRICE_UPDATE_INTERVAL_MIN", "15"))

    # Telegram Bot (tägliche Reports)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Google Gemini (AI-Research, optional)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Google Cloud / Vertex AI (bevorzugt in Cloud Run)
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_LOCATION: str = os.getenv("GCP_LOCATION", "europe-west1")

    # AI Finance Agent
    AI_AGENT_TIME: str = os.getenv("AI_AGENT_TIME", "16:30")

    # Caching
    CACHE_DIR: Path = BASE_DIR / "cache"
    CACHE_TTL_HOURS: int = 12

    # Demo mode (when no API keys configured)
    @property
    def telegram_configured(self) -> bool:
        """True wenn Telegram-Bot konfiguriert ist."""
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID)

    @property
    def vertex_ai_configured(self) -> bool:
        """True wenn Vertex AI via GCP-Projekt konfiguriert ist (Cloud Run)."""
        return bool(self.GCP_PROJECT_ID)

    @property
    def gemini_configured(self) -> bool:
        """True wenn Gemini nutzbar ist (Vertex AI ODER API-Key)."""
        return self.vertex_ai_configured or bool(self.GEMINI_API_KEY)

    @property
    def demo_mode(self) -> bool:
        return not self.FMP_API_KEY or self.FMP_API_KEY == "your_fmp_api_key_here"

    def __init__(self):
        self.CACHE_DIR.mkdir(exist_ok=True)


settings = Settings()
