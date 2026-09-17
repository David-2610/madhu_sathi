"""
Pydantic schemas for IoT devices, telemetry, alerts, health analysis, and AI assistance.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import get_settings
from app.models.hive_alert import AlertSeverity, AlertStatus, AlertType

settings = get_settings()


# ── Hive Device Schemas ───────────────────────────────────────────────────
class HiveDeviceCreate(BaseModel):
    """Payload to register an IoT device to a Hive."""

    device_id: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Unique hardware identifier / serial / MAC address of sensor node",
        examples=["ESP32-NODE-001"],
    )
    device_type: str = Field(
        "ESP32_SENSOR_NODE",
        max_length=50,
        description="Hardware type or model of the device",
    )
    firmware_version: Optional[str] = Field(
        None,
        max_length=50,
        description="Current firmware version",
        examples=["v1.2.0"],
    )


class HiveDeviceResponse(BaseModel):
    """Device details returned by API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    hive_id: int
    device_id: str
    device_type: str
    firmware_version: Optional[str] = None
    is_active: bool
    last_seen_at: Optional[datetime] = None
    device_token: Optional[str] = Field(
        None,
        description="Hardware authentication token. Returned once upon initial device registration.",
    )
    created_at: datetime
    updated_at: datetime


# ── Hive Telemetry Schemas ────────────────────────────────────────────────
class HiveTelemetryCreate(BaseModel):
    """Payload to ingest a periodic sensor telemetry reading."""

    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of observation in UTC",
    )
    temperature_c: Decimal = Field(
        ...,
        description="Internal hive temperature in Celsius (-30.0 to 70.0)",
        examples=[Decimal("34.50")],
    )
    humidity_percent: Decimal = Field(
        ...,
        description="Internal hive relative humidity percentage (0.0 to 100.0)",
        examples=[Decimal("62.50")],
    )
    weight_kg: Decimal = Field(
        ...,
        description="Total hive scale weight in kilograms (>= 0.0)",
        examples=[Decimal("28.40")],
    )
    sound_level: Decimal = Field(
        ...,
        description="Internal sound level in decibels (>= 0.0)",
        examples=[Decimal("45.20")],
    )
    vibration_level: Decimal = Field(
        ...,
        description="Internal vibration level (>= 0.0)",
        examples=[Decimal("0.80")],
    )
    battery_percent: Optional[Decimal] = Field(
        None,
        description="Device battery level percentage (0.0 to 100.0)",
        examples=[Decimal("95.00")],
    )
    device_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional publishing device hardware ID",
    )

    @field_validator("temperature_c")
    @classmethod
    def validate_temperature(cls, v: Decimal) -> Decimal:
        cfg = get_settings()
        if v < Decimal(str(cfg.TELEMETRY_TEMP_MIN_C)) or v > Decimal(str(cfg.TELEMETRY_TEMP_MAX_C)):
            raise ValueError(
                f"Temperature {v}°C is outside physically possible range "
                f"({cfg.TELEMETRY_TEMP_MIN_C}°C to {cfg.TELEMETRY_TEMP_MAX_C}°C)."
            )
        return v

    @field_validator("humidity_percent")
    @classmethod
    def validate_humidity(cls, v: Decimal) -> Decimal:
        cfg = get_settings()
        if v < Decimal(str(cfg.TELEMETRY_HUMIDITY_MIN)) or v > Decimal(str(cfg.TELEMETRY_HUMIDITY_MAX)):
            raise ValueError(
                f"Humidity {v}% is outside valid physical range "
                f"({cfg.TELEMETRY_HUMIDITY_MIN}% to {cfg.TELEMETRY_HUMIDITY_MAX}%)."
            )
        return v

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, v: Decimal) -> Decimal:
        cfg = get_settings()
        if v < Decimal(str(cfg.TELEMETRY_WEIGHT_MIN_KG)) or v > Decimal(str(cfg.TELEMETRY_WEIGHT_MAX_KG)):
            raise ValueError(
                f"Weight {v} kg is outside valid physical range "
                f"({cfg.TELEMETRY_WEIGHT_MIN_KG} to {cfg.TELEMETRY_WEIGHT_MAX_KG} kg)."
            )
        return v

    @field_validator("sound_level")
    @classmethod
    def validate_sound(cls, v: Decimal) -> Decimal:
        cfg = get_settings()
        if v < Decimal(str(cfg.TELEMETRY_SOUND_MIN_DB)) or v > Decimal(str(cfg.TELEMETRY_SOUND_MAX_DB)):
            raise ValueError(
                f"Sound level {v} dB is outside valid physical range "
                f"({cfg.TELEMETRY_SOUND_MIN_DB} to {cfg.TELEMETRY_SOUND_MAX_DB} dB)."
            )
        return v

    @field_validator("vibration_level")
    @classmethod
    def validate_vibration(cls, v: Decimal) -> Decimal:
        cfg = get_settings()
        if v < Decimal(str(cfg.TELEMETRY_VIBRATION_MIN)) or v > Decimal(str(cfg.TELEMETRY_VIBRATION_MAX)):
            raise ValueError(
                f"Vibration level {v} is outside valid physical range "
                f"({cfg.TELEMETRY_VIBRATION_MIN} to {cfg.TELEMETRY_VIBRATION_MAX})."
            )
        return v

    @field_validator("battery_percent")
    @classmethod
    def validate_battery(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < Decimal("0.0") or v > Decimal("100.0"):
                raise ValueError(f"Battery percent {v}% must be between 0.0% and 100.0%.")
        return v


class HiveTelemetryResponse(BaseModel):
    """Telemetry reading returned by API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    hive_id: int
    device_id: Optional[str] = None
    timestamp: datetime
    temperature_c: Decimal
    humidity_percent: Decimal
    weight_kg: Decimal
    sound_level: Decimal
    vibration_level: Decimal
    battery_percent: Optional[Decimal] = None
    is_simulated: bool
    is_duplicate: bool = Field(
        False,
        description="Whether this reading was deduplicated idempotently without re-inserting.",
    )
    created_at: datetime


# ── Hive Alert Schemas ────────────────────────────────────────────────────
class HiveAlertResponse(BaseModel):
    """Hive health alert details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    hive_id: int
    telemetry_id: Optional[int] = None
    alert_type: str
    severity: AlertSeverity
    title: str
    message: str
    recommended_action: str
    status: AlertStatus
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ── Hive Health Summary Schemas ───────────────────────────────────────────
class HiveHealthMetrics(BaseModel):
    """Statistical and real-time metrics for a hive."""

    latest_reading: Optional[HiveTelemetryResponse] = None
    avg_temperature_24h: Optional[Decimal] = None
    avg_humidity_24h: Optional[Decimal] = None
    weight_delta_24h: Optional[Decimal] = None
    active_alerts_count: int = 0
    last_seen_at: Optional[datetime] = None


class HiveHealthSummaryResponse(BaseModel):
    """Comprehensive health summary evaluated by the rule-based engine."""

    hive_id: int
    hive_code: str
    health_status: str = Field(
        ...,
        description="High level status: HEALTHY | NEEDS_ATTENTION | CRITICAL",
        examples=["HEALTHY"],
    )
    severity: AlertSeverity
    summary: str
    metrics: HiveHealthMetrics
    anomalies: List[str] = []
    active_alerts: List[HiveAlertResponse] = []


# ── AI Assistance Schemas ─────────────────────────────────────────────────
class AIAssistantRequest(BaseModel):
    """Request for AI-assisted interpretation of hive conditions."""

    query: Optional[str] = Field(
        None,
        description="Optional question from beekeeper regarding recent conditions or recommendations",
        examples=["Why did the weight drop suddenly this morning?"],
    )


class AIAssistantResponse(BaseModel):
    """AI explanation and actionable recommendations."""

    hive_id: int
    condition_summary: str
    explanation: str
    recommended_steps: List[str]
    disclaimer: str = (
        "Possible abnormal hive condition detected. Note: Telemetry anomalies indicate "
        "environmental or behavioral variations and do NOT constitute a confirmed disease diagnosis. "
        "Physical hive inspection is required."
    )
    is_mock: bool = True
    provider: str = "MOCK_AI"


# ── IoT Simulator Schemas ─────────────────────────────────────────────────
class SimulatorScenario(str, PyEnum):
    NORMAL = "NORMAL"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    LOW_HUMIDITY = "LOW_HUMIDITY"
    RAPID_WEIGHT_DROP = "RAPID_WEIGHT_DROP"
    ABNORMAL_SOUND = "ABNORMAL_SOUND"
    MISSING_TELEMETRY = "MISSING_TELEMETRY"


class SimulatorRunRequest(BaseModel):
    """Payload to trigger an IoT simulation scenario."""

    scenario: SimulatorScenario = Field(
        SimulatorScenario.NORMAL,
        description="Scenario to simulate",
    )


class SimulatorRunResponse(BaseModel):
    """Result of running an IoT simulation scenario."""

    scenario: SimulatorScenario
    telemetry: HiveTelemetryResponse
    health_status: str
    alerts_generated: List[HiveAlertResponse] = []
