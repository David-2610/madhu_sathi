"""
Tests for application configuration loading.
"""

from app.core.config import Settings, get_settings


def test_settings_defaults():
    """Settings should load with defined defaults when no .env is present."""
    s = Settings()
    assert s.APP_NAME == "Honey Chain"
    assert s.APP_ENV == "development"
    assert s.APP_VERSION == "0.1.0"


def test_get_settings_returns_singleton():
    """get_settings() must return the same cached instance on repeated calls."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
