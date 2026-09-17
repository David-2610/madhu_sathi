"""
Application configuration.

Settings are loaded from environment variables (or a .env file via
python-dotenv, which Pydantic Settings handles automatically).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    # ── Application ────────────────────────────────────────────────────────
    APP_NAME: str = "Honey Chain"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"  # development | staging | production

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/honeychain"

    # ── Security ───────────────────────────────────────────────────────────
    # Generate a strong key:  openssl rand -hex 32
    SECRET_KEY: str = "change-me-in-production"

    # ── JWT ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-jwt-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour

    # ── QR & Traceability (Phase 5) ────────────────────────────────────────
    BASE_URL: str = "http://localhost:8000"

    # ── Blockchain Abstraction (Phase 5) ───────────────────────────────────
    BLOCKCHAIN_PROVIDER: str = "mock"  # "mock" | "evm"
    BLOCKCHAIN_RPC_URL: str | None = None
    BLOCKCHAIN_CONTRACT_ADDRESS: str | None = None

    # ── IoT & Telemetry Physical Bounds (Phase 7) ──────────────────────────
    TELEMETRY_TEMP_MIN_C: float = -30.0
    TELEMETRY_TEMP_MAX_C: float = 70.0
    TELEMETRY_HUMIDITY_MIN: float = 0.0
    TELEMETRY_HUMIDITY_MAX: float = 100.0
    TELEMETRY_WEIGHT_MIN_KG: float = 0.0
    TELEMETRY_WEIGHT_MAX_KG: float = 500.0
    TELEMETRY_SOUND_MIN_DB: float = 0.0
    TELEMETRY_SOUND_MAX_DB: float = 150.0
    TELEMETRY_VIBRATION_MIN: float = 0.0
    TELEMETRY_VIBRATION_MAX: float = 100.0

    # ── Hive Health & Anomaly Thresholds (Phase 7) ─────────────────────────
    HIVE_TEMP_BROOD_MIN_C: float = 32.0     # Normal brood nest ~32-36C
    HIVE_TEMP_BROOD_MAX_C: float = 37.0     # Over 37C indicates elevated heat
    HIVE_TEMP_CRITICAL_HIGH_C: float = 41.0 # Acute thermal stress
    HIVE_TEMP_CRITICAL_LOW_C: float = 25.0  # Acute chilling / cluster break

    HIVE_HUMIDITY_MIN_PERCENT: float = 40.0 # Low humidity / dehydration risk
    HIVE_HUMIDITY_MAX_PERCENT: float = 75.0 # Moisture buildup / condensation risk

    HIVE_WEIGHT_DROP_ALERT_KG: float = 1.5  # Sudden drop (swarming or theft)
    HIVE_SOUND_ALERT_DB: float = 75.0       # High agitation/piping
    HIVE_VIBRATION_ALERT: float = 4.0       # Physical agitation

    HIVE_TELEMETRY_STALE_MINUTES: int = 120 # Gap indicating missing telemetry
    ALERT_COOLDOWN_MINUTES: int = 30        # Alert deduplication cooldown

    # ── MQTT Ingestion (Phase 7) ───────────────────────────────────────────
    MQTT_PROVIDER: str = "mock"             # "mock" | "paho"
    MQTT_BROKER_HOST: str | None = None
    MQTT_BROKER_PORT: int = 1883
    MQTT_TOPIC_PREFIX: str = "honeychain/hives"

    # ── AI Assistance (Phase 7) ────────────────────────────────────────────
    AI_PROVIDER: str = "mock"               # "mock" | "gemini"
    GEMINI_API_KEY: str | None = None

    # ── Pydantic Settings config ───────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (created once per process)."""
    return Settings()
