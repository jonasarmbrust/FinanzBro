"""Tests für den Vertex AI Service."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


class TestGetClient:
    """Tests für die Client-Erstellung."""

    def setup_method(self):
        """Reset daily counter between tests."""
        from services import vertex_ai
        vertex_ai._daily_call_count = 0
        vertex_ai._daily_call_date = None

    def test_vertex_ai_client_when_configured(self):
        """Vertex AI Client wird erstellt wenn GCP_PROJECT_ID gesetzt."""
        from services.vertex_ai import get_client

        mock_client = MagicMock()
        with patch("services.vertex_ai.settings") as mock_settings, \
             patch("google.genai.Client", return_value=mock_client) as mock_constructor:
            mock_settings.vertex_ai_configured = True
            mock_settings.GCP_PROJECT_ID = "test-project"
            mock_settings.GCP_LOCATION = "europe-west1"
            mock_settings.GEMINI_API_KEY = ""

            client = get_client()

            mock_constructor.assert_called_once_with(
                vertexai=True,
                project="test-project",
                location="europe-west1",
            )

    def test_api_key_fallback(self):
        """API Key Client als Fallback wenn kein GCP-Projekt."""
        from services.vertex_ai import get_client

        mock_client = MagicMock()
        with patch("services.vertex_ai.settings") as mock_settings, \
             patch("google.genai.Client", return_value=mock_client) as mock_constructor:
            mock_settings.vertex_ai_configured = False
            mock_settings.GCP_PROJECT_ID = ""
            mock_settings.GEMINI_API_KEY = "test-api-key"

            client = get_client()

            mock_constructor.assert_called_once_with(api_key="test-api-key")

    def test_raises_when_nothing_configured(self):
        """RuntimeError wenn weder Vertex AI noch API Key konfiguriert."""
        from services.vertex_ai import get_client

        with patch("services.vertex_ai.settings") as mock_settings:
            mock_settings.vertex_ai_configured = False
            mock_settings.GCP_PROJECT_ID = ""
            mock_settings.GEMINI_API_KEY = ""

            with pytest.raises(RuntimeError, match="Weder Vertex AI noch Gemini"):
                get_client()

    def test_daily_limit_blocks_after_max(self):
        """Nach 100 Calls wird RuntimeError geworfen."""
        from services import vertex_ai
        vertex_ai._daily_call_count = 100  # Already at limit
        vertex_ai._daily_call_date = vertex_ai.date.today()

        with pytest.raises(RuntimeError, match="Tägliches AI-Call-Limit"):
            vertex_ai.get_client()

    def test_daily_limit_resets_at_midnight(self):
        """Counter resettet sich an neuem Tag."""
        from services import vertex_ai
        from datetime import date, timedelta
        vertex_ai._daily_call_count = 100
        vertex_ai._daily_call_date = date.today() - timedelta(days=1)  # Yesterday

        # Should NOT raise — new day resets counter
        mock_client = MagicMock()
        with patch("services.vertex_ai.settings") as mock_settings, \
             patch("google.genai.Client", return_value=mock_client):
            mock_settings.vertex_ai_configured = False
            mock_settings.GEMINI_API_KEY = "test-key"
            vertex_ai.get_client()

        assert vertex_ai._daily_call_count == 1


class TestGroundedConfig:
    """Tests für Search Grounding Config."""

    def test_returns_tools_config(self):
        """Config enthält Google Search Tool."""
        from services.vertex_ai import get_grounded_config

        config = get_grounded_config()

        assert "tools" in config
        assert len(config["tools"]) == 1


class TestContextCache:
    """Tests für Context Caching."""

    def test_get_cached_content_returns_none_initially(self):
        """Ohne Cache → None."""
        from services import vertex_ai
        vertex_ai._active_cache_name = None

        result = vertex_ai.get_cached_content()
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_skips_without_vertex_ai(self):
        """Context Caching wird übersprungen ohne Vertex AI."""
        from services.vertex_ai import cache_portfolio_context

        mock_summary = MagicMock()

        with patch("services.vertex_ai.settings") as mock_settings:
            mock_settings.vertex_ai_configured = False

            result = await cache_portfolio_context(mock_summary)

        assert result is None


class TestConfigSettings:
    """Tests für die Vertex AI Config-Properties."""

    def test_vertex_ai_configured_true(self):
        """vertex_ai_configured ist True mit GCP_PROJECT_ID."""
        with patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project"}):
            from config import Settings
            s = Settings()
            s.GCP_PROJECT_ID = "test-project"
            assert s.vertex_ai_configured is True

    def test_vertex_ai_configured_false(self):
        """vertex_ai_configured ist False ohne GCP_PROJECT_ID."""
        from config import Settings
        s = Settings()
        s.GCP_PROJECT_ID = ""
        assert s.vertex_ai_configured is False

    def test_gemini_configured_via_vertex(self):
        """gemini_configured ist True wenn Vertex AI konfiguriert."""
        from config import Settings
        s = Settings()
        s.GCP_PROJECT_ID = "test-project"
        s.GEMINI_API_KEY = ""
        assert s.gemini_configured is True

    def test_gemini_configured_via_api_key(self):
        """gemini_configured ist True wenn API Key vorhanden."""
        from config import Settings
        s = Settings()
        s.GCP_PROJECT_ID = ""
        s.GEMINI_API_KEY = "test-key"
        assert s.gemini_configured is True

    def test_gemini_configured_neither(self):
        """gemini_configured ist False ohne Vertex AI und ohne API Key."""
        from config import Settings
        s = Settings()
        s.GCP_PROJECT_ID = ""
        s.GEMINI_API_KEY = ""
        assert s.gemini_configured is False
