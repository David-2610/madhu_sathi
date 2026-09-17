"""
AI Provider factory for Honey Chain.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.services.ai.base import AIExplanation, AIProvider
from app.services.ai.gemini_provider import GeminiAIProvider
from app.services.ai.mock_provider import MockAIProvider

settings = get_settings()


@lru_cache
def get_ai_provider() -> AIProvider:
    """Return configured AI assistance provider."""
    provider_type = (settings.AI_PROVIDER or "mock").lower()
    if provider_type == "gemini":
        return GeminiAIProvider()
    return MockAIProvider()
