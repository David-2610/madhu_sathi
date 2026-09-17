"""
CRUD operations for IoT devices, telemetry, and alerts.

Hardening features:
- Secure hardware device token generation & SHA-256 hashing.
- Telemetry deduplication and idempotency check.
- Strict alert lifecycle state machine (OPEN -> ACKNOWLEDGED -> RESOLVED).
"""

from datetime import datetime, timezone
import hashlib
import secrets
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.hive_alert import AlertStatus, HiveAlert
from app.models.hive_device import HiveDevice
from app.models.hive_telemetry import HiveTelemetry
from app.schemas.iot import HiveDeviceCreate, HiveTelemetryCreate


class TelemetryConflictError(Exception):
    """Raised when conflicting telemetry data is submitted at an existing timestamp."""
    pass


class InvalidAlertStateError(Exception):
    """Raised when an illegal alert status transition is attempted."""
    pass


# ── Device Operations ─────────────────────────────────────────────────────
def create_hive_device(
    db: Session,
    hive_id: int,
    payload: HiveDeviceCreate,
) -> Tuple[HiveDevice, str]:
    """
    Register a new sensor node hardware device to a hive.
    Generates a cryptographically random device secret, stores its SHA-256 hash,
    and returns (device, raw_token) so the raw token can be displayed once.
    """
    raw_token = f"hc_dev_{secrets.token_urlsafe(24)}"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    device = HiveDevice(
        hive_id=hive_id,
        device_id=payload.device_id,
        device_type=payload.device_type,
        firmware_version=payload.firmware_version,
        device_token_hash=token_hash,
        is_active=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    setattr(device, "device_token", raw_token)
    return device, raw_token


def get_hive_device_by_id(db: Session, device_id: int) -> Optional[HiveDevice]:
    """Retrieve device by internal primary key."""
    return db.get(HiveDevice, device_id)


def get_hive_device_by_hardware_id(db: Session, hardware_id: str) -> Optional[HiveDevice]:
    """Retrieve device by unique hardware device_id."""
    return (
        db.query(HiveDevice)
        .filter(HiveDevice.device_id == hardware_id)
        .first()
    )


def get_device_by_token_hash(db: Session, token_hash: str) -> Optional[HiveDevice]:
    """Lookup active device by SHA-256 token hash."""
    return (
        db.query(HiveDevice)
        .filter(
            HiveDevice.device_token_hash == token_hash,
            HiveDevice.is_active.is_(True),
        )
        .first()
    )


def list_devices_by_hive(
    db: Session,
    hive_id: int,
    skip: int = 0,
    limit: int = 50,
) -> List[HiveDevice]:
    """List devices registered to a hive with pagination."""
    return (
        db.query(HiveDevice)
        .filter(HiveDevice.hive_id == hive_id)
        .order_by(HiveDevice.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def touch_device_last_seen(
    db: Session,
    hardware_id: str,
    seen_at: Optional[datetime] = None,
) -> Optional[HiveDevice]:
    """Update last_seen_at timestamp when a device publishes data."""
    device = get_hive_device_by_hardware_id(db, hardware_id)
    if device is not None:
        device.last_seen_at = seen_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(device)
    return device


# ── Telemetry Operations ──────────────────────────────────────────────────
def record_hive_telemetry(
    db: Session,
    hive_id: int,
    payload: HiveTelemetryCreate,
    is_simulated: bool = False,
) -> Tuple[HiveTelemetry, bool]:
    """
    Store an ingested telemetry reading in the database.
    Returns (reading, is_duplicate).

    Idempotency:
    - If exact duplicate timestamp & values: returns existing without error.
    - If conflicting values for identical timestamp: raises TelemetryConflictError.
    """
    ts = payload.timestamp or datetime.now(timezone.utc)
    existing = (
        db.query(HiveTelemetry)
        .filter(HiveTelemetry.hive_id == hive_id, HiveTelemetry.timestamp == ts)
        .first()
    )
    if existing is not None:
        if (
            existing.temperature_c == payload.temperature_c
            and existing.humidity_percent == payload.humidity_percent
            and existing.weight_kg == payload.weight_kg
            and existing.sound_level == payload.sound_level
            and existing.vibration_level == payload.vibration_level
        ):
            return existing, True
        raise TelemetryConflictError(
            f"Conflicting telemetry reading already exists for hive {hive_id} at timestamp {ts.isoformat()}."
        )

    reading = HiveTelemetry(
        hive_id=hive_id,
        device_id=payload.device_id,
        timestamp=ts,
        temperature_c=payload.temperature_c,
        humidity_percent=payload.humidity_percent,
        weight_kg=payload.weight_kg,
        sound_level=payload.sound_level,
        vibration_level=payload.vibration_level,
        battery_percent=payload.battery_percent,
        is_simulated=is_simulated,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    if payload.device_id:
        touch_device_last_seen(db, payload.device_id, reading.timestamp)

    return reading, False


def list_hive_telemetry(
    db: Session,
    hive_id: int,
    skip: int = 0,
    limit: int = 100,
) -> List[HiveTelemetry]:
    """Retrieve historical telemetry readings for a hive, newest first."""
    return (
        db.query(HiveTelemetry)
        .filter(HiveTelemetry.hive_id == hive_id)
        .order_by(HiveTelemetry.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_latest_hive_telemetry(db: Session, hive_id: int) -> Optional[HiveTelemetry]:
    """Retrieve the most recent telemetry reading for a hive."""
    return (
        db.query(HiveTelemetry)
        .filter(HiveTelemetry.hive_id == hive_id)
        .order_by(HiveTelemetry.timestamp.desc())
        .first()
    )


# ── Alert Operations ──────────────────────────────────────────────────────
def list_hive_alerts(
    db: Session,
    hive_id: int,
    status_filter: Optional[AlertStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[HiveAlert]:
    """Retrieve alerts for a hive, optionally filtered by status with pagination."""
    query = db.query(HiveAlert).filter(HiveAlert.hive_id == hive_id)
    if status_filter is not None:
        query = query.filter(HiveAlert.status == status_filter)
    return (
        query.order_by(HiveAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_alert_by_id(db: Session, alert_id: int) -> Optional[HiveAlert]:
    """Retrieve alert by primary key."""
    return db.get(HiveAlert, alert_id)


def acknowledge_alert(db: Session, alert: HiveAlert) -> HiveAlert:
    """Transition alert to ACKNOWLEDGED enforcing strict OPEN -> ACKNOWLEDGED."""
    if alert.status == AlertStatus.ACKNOWLEDGED:
        raise InvalidAlertStateError("Alert is already acknowledged.")
    if alert.status == AlertStatus.RESOLVED:
        raise InvalidAlertStateError("Cannot acknowledge an alert that is already resolved.")

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(db: Session, alert: HiveAlert) -> HiveAlert:
    """Transition alert to RESOLVED enforcing strict OPEN/ACKNOWLEDGED -> RESOLVED."""
    if alert.status == AlertStatus.RESOLVED:
        raise InvalidAlertStateError("Alert is already resolved.")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert
