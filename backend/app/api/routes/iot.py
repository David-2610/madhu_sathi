"""
API routes for IoT Devices, Telemetry, Health Engine, Alerts, and AI Assistance.

Phase 8 Hardening:
- Dual ingestion authentication: X-Device-Token (hardware) or Bearer JWT (beekeeper/simulator).
- Telemetry deduplication and idempotency check.
- Strict alert lifecycle transitions: OPEN -> ACKNOWLEDGED -> RESOLVED.
- Consistent pagination, Decimal serialization, and complete OpenAPI error response models.
"""

from decimal import Decimal
import hashlib
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from jose import JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.beekeeper import get_current_beekeeper
from app.core.security import decode_access_token
from app.crud.beekeeper import get_beekeeper_by_user_id
from app.crud.hive import get_hive_by_id
from app.crud.iot import (
    InvalidAlertStateError,
    TelemetryConflictError,
    acknowledge_alert,
    create_hive_device,
    get_alert_by_id,
    get_device_by_token_hash,
    get_hive_device_by_hardware_id,
    get_latest_hive_telemetry,
    list_devices_by_hive,
    list_hive_alerts,
    list_hive_telemetry,
    record_hive_telemetry,
    resolve_alert,
)
from app.crud.user import get_user_by_id
from app.db import get_db
from app.models.beekeeper import BeekeeperProfile
from app.models.hive import Hive
from app.models.hive_alert import AlertStatus
from app.models.hive_device import HiveDevice
from app.models.user import UserRole
from app.schemas.common import ErrorResponse
from app.schemas.iot import (
    AIAssistantRequest,
    AIAssistantResponse,
    HiveAlertResponse,
    HiveDeviceCreate,
    HiveDeviceResponse,
    HiveHealthSummaryResponse,
    HiveTelemetryCreate,
    HiveTelemetryResponse,
    SimulatorRunRequest,
    SimulatorRunResponse,
)
from app.services.ai import get_ai_provider
from app.services.health_engine import HealthEngine
from app.services.iot_simulator import IoTSimulator
from app.services.mqtt import get_mqtt_provider

router = APIRouter(prefix="/beekeeper", tags=["IoT Devices & Hive Health"])


def _get_verified_hive(db: Session, hive_id: int, beekeeper: BeekeeperProfile) -> Hive:
    """Helper to verify hive exists and belongs to the authenticated beekeeper."""
    hive = get_hive_by_id(db, hive_id)
    if hive is None or hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )
    return hive


def get_telemetry_auth(
    hive_id: int,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> Tuple[Hive, Optional[HiveDevice], Optional[BeekeeperProfile]]:
    """
    Authenticate telemetry ingestion caller via either:
    1. X-Device-Token header (hardware sensor node)
    2. Authorization: Bearer <JWT> header (authenticated beekeeper, simulator, web UI)
    """
    hive = get_hive_by_id(db, hive_id)
    if hive is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )

    if x_device_token:
        token_hash = hashlib.sha256(x_device_token.encode("utf-8")).hexdigest()
        device = get_device_by_token_hash(db, token_hash)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive device token.",
            )
        if device.hive_id != hive_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device token does not belong to this hive.",
            )
        return hive, device, None

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Use Bearer JWT or X-Device-Token header.",
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        user_id = decode_access_token(token)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )
    if user.role != UserRole.BEEKEEPER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: BEEKEEPER role required.",
        )

    profile = get_beekeeper_by_user_id(db, user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Beekeeper profile not found.",
        )
    if hive.apiary.beekeeper_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )

    return hive, None, profile


# ── Device Endpoints ──────────────────────────────────────────────────────
@router.post(
    "/hives/{hive_id}/devices",
    response_model=HiveDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an IoT device to a hive",
    description=(
        "Register an IoT hardware sensor node to the beekeeper's hive. "
        "Generates a unique hardware device token returned once upon registration."
    ),
    responses={
        201: {"description": "Device registered successfully"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
        409: {"model": ErrorResponse, "description": "Device ID already registered"},
    },
)
def register_device(
    hive_id: int,
    payload: HiveDeviceCreate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HiveDeviceResponse:
    """Register an IoT hardware sensor node to the beekeeper's hive."""
    _get_verified_hive(db, hive_id, beekeeper)

    existing = get_hive_device_by_hardware_id(db, payload.device_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with ID '{payload.device_id}' is already registered.",
        )

    try:
        device, raw_token = create_hive_device(db, hive_id, payload)
        resp = HiveDeviceResponse.model_validate(device)
        resp.device_token = raw_token
        return resp
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with ID '{payload.device_id}' already exists.",
        )


@router.get(
    "/hives/{hive_id}/devices",
    response_model=List[HiveDeviceResponse],
    summary="List devices registered to a hive",
    description="Retrieve all hardware devices registered to this hive with optional pagination.",
    responses={
        200: {"description": "List of registered devices"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
    },
)
def list_devices(
    hive_id: int,
    skip: int = Query(0, ge=0, description="Offset items"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HiveDeviceResponse]:
    """Retrieve all hardware devices registered to this hive."""
    _get_verified_hive(db, hive_id, beekeeper)
    devices = list_devices_by_hive(db, hive_id, skip=skip, limit=limit)
    return [HiveDeviceResponse.model_validate(d) for d in devices]


# ── Telemetry Endpoints ───────────────────────────────────────────────────
@router.post(
    "/hives/{hive_id}/telemetry",
    response_model=HiveTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest sensor telemetry reading",
    description=(
        "Ingest a periodic sensor telemetry reading for a hive. "
        "Supports authentication via X-Device-Token header (hardware sensor nodes) "
        "or Authorization: Bearer JWT (beekeepers and development simulator). "
        "Evaluates hive health and generates alerts with deduplication cooldown."
    ),
    responses={
        201: {"description": "Telemetry ingested successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input or profile error"},
        401: {"model": ErrorResponse, "description": "Unauthorized or invalid credentials"},
        403: {"model": ErrorResponse, "description": "Forbidden device or role"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
        409: {"model": ErrorResponse, "description": "Conflicting telemetry at identical timestamp"},
        422: {"model": ErrorResponse, "description": "Physical bounds validation error"},
    },
)
def ingest_telemetry(
    hive_id: int,
    payload: HiveTelemetryCreate,
    response: Response,
    auth_info: Tuple[Hive, Optional[HiveDevice], Optional[BeekeeperProfile]] = Depends(get_telemetry_auth),
    db: Session = Depends(get_db),
) -> HiveTelemetryResponse:
    """
    Ingest a periodic sensor telemetry reading for a hive.
    Runs automated anomaly evaluation and alert generation.
    """
    hive, device, _ = auth_info

    if device and not payload.device_id:
        payload.device_id = device.device_id

    try:
        reading, is_duplicate = record_hive_telemetry(db, hive_id, payload, is_simulated=False)
    except TelemetryConflictError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err

    if is_duplicate:
        response.status_code = status.HTTP_200_OK
        resp = HiveTelemetryResponse.model_validate(reading)
        resp.is_duplicate = True
        return resp

    # 2. Publish to MQTT abstraction
    mqtt = get_mqtt_provider()
    telemetry_dict = {
        "timestamp": reading.timestamp.isoformat(),
        "temperature_c": float(reading.temperature_c),
        "humidity_percent": float(reading.humidity_percent),
        "weight_kg": float(reading.weight_kg),
        "sound_level": float(reading.sound_level),
        "vibration_level": float(reading.vibration_level),
        "battery_percent": float(reading.battery_percent) if reading.battery_percent else None,
        "device_id": reading.device_id,
    }
    mqtt.publish_telemetry(hive_id, telemetry_dict)

    # 3. Evaluate health & trigger deduplicated alerts
    HealthEngine.evaluate_telemetry(db, hive, reading)

    return HiveTelemetryResponse.model_validate(reading)


@router.get(
    "/hives/{hive_id}/telemetry",
    response_model=List[HiveTelemetryResponse],
    summary="Get historical telemetry readings for a hive",
    description="Retrieve historical telemetry readings, newest first.",
    responses={
        200: {"description": "List of historical telemetry readings"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
    },
)
def get_telemetry_history(
    hive_id: int,
    skip: int = Query(0, ge=0, description="Offset items"),
    limit: int = Query(100, ge=1, le=1000, description="Max readings to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HiveTelemetryResponse]:
    """Retrieve historical telemetry readings, newest first."""
    _get_verified_hive(db, hive_id, beekeeper)
    readings = list_hive_telemetry(db, hive_id, skip=skip, limit=limit)
    return [HiveTelemetryResponse.model_validate(r) for r in readings]


# ── Alert Endpoints ───────────────────────────────────────────────────────
@router.get(
    "/hives/{hive_id}/alerts",
    response_model=List[HiveAlertResponse],
    summary="List alerts for a hive",
    description="Retrieve alerts generated for this hive with optional status filter and pagination.",
    responses={
        200: {"description": "List of hive alerts"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
    },
)
def get_hive_alerts(
    hive_id: int,
    status_filter: Optional[AlertStatus] = Query(None, alias="status", description="Filter by status (OPEN, ACKNOWLEDGED, RESOLVED)"),
    skip: int = Query(0, ge=0, description="Offset items"),
    limit: int = Query(50, ge=1, le=200, description="Max alerts to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HiveAlertResponse]:
    """Retrieve alerts generated for this hive."""
    _get_verified_hive(db, hive_id, beekeeper)
    alerts = list_hive_alerts(db, hive_id, status_filter=status_filter, skip=skip, limit=limit)
    return [HiveAlertResponse.model_validate(a) for a in alerts]


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=HiveAlertResponse,
    summary="Acknowledge an alert",
    description="Mark an OPEN alert as ACKNOWLEDGED. Rejects already acknowledged or resolved alerts with HTTP 400.",
    responses={
        200: {"description": "Alert acknowledged"},
        400: {"model": ErrorResponse, "description": "Invalid alert status transition"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Alert not found"},
    },
)
def acknowledge_hive_alert(
    alert_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HiveAlertResponse:
    """Mark an open alert as ACKNOWLEDGED."""
    alert = get_alert_by_id(db, alert_id)
    if alert is None or alert.hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )
    try:
        acknowledged = acknowledge_alert(db, alert)
    except InvalidAlertStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    return HiveAlertResponse.model_validate(acknowledged)


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=HiveAlertResponse,
    summary="Resolve an alert",
    description="Mark an OPEN or ACKNOWLEDGED alert as RESOLVED. Rejects already resolved alerts with HTTP 400.",
    responses={
        200: {"description": "Alert resolved"},
        400: {"model": ErrorResponse, "description": "Invalid alert status transition"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Alert not found"},
    },
)
def resolve_hive_alert(
    alert_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HiveAlertResponse:
    """Mark an alert as RESOLVED."""
    alert = get_alert_by_id(db, alert_id)
    if alert is None or alert.hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )
    try:
        resolved = resolve_alert(db, alert)
    except InvalidAlertStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    return HiveAlertResponse.model_validate(resolved)


# ── Health Summary Endpoint ───────────────────────────────────────────────
@router.get(
    "/hives/{hive_id}/health",
    response_model=HiveHealthSummaryResponse,
    summary="Get overall health and anomaly summary for a hive",
    description=(
        "Evaluates rule-based health status, 24-hour moving metrics, active alerts, "
        "and production-safe staleness detection for the hive."
    ),
    responses={
        200: {"description": "Hive health summary"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
    },
)
def get_hive_health(
    hive_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HiveHealthSummaryResponse:
    """
    Evaluates rule-based health status, 24-hour moving metrics, active alerts,
    and staleness for the hive.
    """
    hive = _get_verified_hive(db, hive_id, beekeeper)
    return HealthEngine.get_health_summary(db, hive)


# ── AI Assistant Endpoint ─────────────────────────────────────────────────
@router.post(
    "/hives/{hive_id}/assistant",
    response_model=AIAssistantResponse,
    summary="Get AI-assisted explanation and actionable recommendations",
    description=(
        "Summarizes recent conditions and provides plain-language explanations "
        "and inspection steps with mandatory non-diagnostic disclaimers. "
        "Falls back safely if AI provider is unreachable."
    ),
    responses={
        200: {"description": "AI explanation and recommendations"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
    },
)
def ask_hive_assistant(
    hive_id: int,
    payload: Optional[AIAssistantRequest] = None,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> AIAssistantResponse:
    """
    Summarizes recent conditions and provides plain-language explanations
    and inspection steps without claiming disease certainty.
    """
    hive = _get_verified_hive(db, hive_id, beekeeper)
    summary = HealthEngine.get_health_summary(db, hive)

    metrics_dict = {
        "temperature_c": float(summary.metrics.latest_reading.temperature_c) if summary.metrics.latest_reading else None,
        "humidity_percent": float(summary.metrics.latest_reading.humidity_percent) if summary.metrics.latest_reading else None,
        "weight_kg": float(summary.metrics.latest_reading.weight_kg) if summary.metrics.latest_reading else None,
        "sound_level": float(summary.metrics.latest_reading.sound_level) if summary.metrics.latest_reading else None,
        "vibration_level": float(summary.metrics.latest_reading.vibration_level) if summary.metrics.latest_reading else None,
        "active_alerts_count": summary.metrics.active_alerts_count,
    }

    query = payload.query if payload else None
    ai_provider = get_ai_provider()
    explanation = ai_provider.generate_explanation(
        hive_id=hive.id,
        hive_code=hive.hive_code,
        metrics_summary=metrics_dict,
        anomalies=summary.anomalies,
        query=query,
    )

    return AIAssistantResponse(
        hive_id=hive.id,
        condition_summary=explanation.condition_summary,
        explanation=explanation.explanation,
        recommended_steps=explanation.recommended_steps,
        disclaimer=explanation.disclaimer,
        is_mock=explanation.is_mock,
        provider=explanation.provider,
    )


# ── Simulator Endpoint (Dev Only) ─────────────────────────────────────────
@router.post(
    "/hives/{hive_id}/simulator/run",
    response_model=SimulatorRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run an IoT telemetry simulation scenario (Development Only)",
    description=(
        "Generates scenario-specific simulated telemetry (NORMAL, HIGH_TEMPERATURE, "
        "LOW_HUMIDITY, RAPID_WEIGHT_DROP, ABNORMAL_SOUND, MISSING_TELEMETRY), "
        "persists it with is_simulated=True, and triggers health evaluation."
    ),
    responses={
        201: {"description": "Simulation scenario executed"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
    },
)
def run_simulation_scenario(
    hive_id: int,
    payload: SimulatorRunRequest,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> SimulatorRunResponse:
    """
    Generates scenario-specific simulated telemetry, persists it with is_simulated=True,
    and triggers health evaluation.
    """
    hive = _get_verified_hive(db, hive_id, beekeeper)

    latest = get_latest_hive_telemetry(db, hive_id)
    prev_weight = latest.weight_kg if latest else Decimal("26.50")

    sim_payload = IoTSimulator.generate_payload_for_scenario(
        scenario=payload.scenario,
        previous_weight=prev_weight,
    )

    # 1. Record simulated telemetry
    reading, _ = record_hive_telemetry(db, hive_id, sim_payload, is_simulated=True)

    # 2. Publish to MQTT abstraction
    mqtt = get_mqtt_provider()
    mqtt.publish_telemetry(hive_id, {
        "timestamp": reading.timestamp.isoformat(),
        "temperature_c": float(reading.temperature_c),
        "humidity_percent": float(reading.humidity_percent),
        "weight_kg": float(reading.weight_kg),
        "sound_level": float(reading.sound_level),
        "vibration_level": float(reading.vibration_level),
        "is_simulated": True,
        "scenario": payload.scenario.value,
    })

    # 3. Evaluate health
    _, _, alerts = HealthEngine.evaluate_telemetry(db, hive, reading)
    health_summary = HealthEngine.get_health_summary(db, hive)

    return SimulatorRunResponse(
        scenario=payload.scenario,
        telemetry=HiveTelemetryResponse.model_validate(reading),
        health_status=health_summary.health_status,
        alerts_generated=[HiveAlertResponse.model_validate(a) for a in alerts],
    )
