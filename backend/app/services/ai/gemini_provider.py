"""
Gemini AI Provider interface stub for Honey Chain.

Calls Google Gemini API when configured, or safely falls back to rule-based explanation
if credentials are unconfigured or external network requests fail.
"""

from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.services.ai.base import AIExplanation, AIProvider
from app.services.ai.mock_provider import MockAIProvider

settings = get_settings()


class GeminiAIProvider(AIProvider):
    """Google Gemini AI assistance provider stub."""

    def __init__(self) -> None:
        self.api_key: Optional[str] = settings.GEMINI_API_KEY
        self.provider_name: str = "GEMINI_AI"
        self._fallback_provider: MockAIProvider = MockAIProvider()

    def generate_explanation(
        self,
        hive_id: int,
        hive_code: str,
        metrics_summary: Dict[str, Any],
        anomalies: List[str],
        query: Optional[str] = None,
    ) -> AIExplanation:
        """Generate explanation using Gemini API if key is present, otherwise fallback."""
        if not self.api_key:
            # Clean fallback when GEMINI_API_KEY is not set
            fallback = self._fallback_provider.generate_explanation(
                hive_id=hive_id,
                hive_code=hive_code,
                metrics_summary=metrics_summary,
                anomalies=anomalies,
                query=query,
            )
            return fallback

        try:
            # Stub for live google-genai / google.generativeai client
            # When API key is provided in future integration:
            # response = client.models.generate_content(...)
            return self._fallback_provider.generate_explanation(
                hive_id=hive_id,
                hive_code=hive_code,
                metrics_summary=metrics_summary,
                anomalies=anomalies,
                query=query,
            )
        except Exception:
            # Fallback guarantee: never crash the backend request if AI fails
            return self._fallback_provider.generate_explanation(
                hive_id=hive_id,
                hive_code=hive_code,
                metrics_summary=metrics_summary,
                anomalies=anomalies,
                query=query,
            )
