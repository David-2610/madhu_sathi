"""
IoT Bridge Service — Honey Chain / Madhu Sathi

Bridges the deployed IoT Mock Server (https://iotmockserver.vercel.app)
with the main FastAPI backend.

Data Flow:
  Deployed IoT Server (https://iotmockserver.vercel.app/api/v1/iot-data)
    -> polls every 5 seconds via lightweight REST
    -> directly ingests telemetry into the backend DB pipeline
    -> triggers HealthEngine anomaly evaluation, alert generation, and WebSocket broadcast
    -> triggers Gemini AI explanation when anomalies occur
    -> Frontend (Android app) reflects updates via WebSocket or on refresh
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.websockets import manager
from app.crud.iot import TelemetryConflictError, record_hive_telemetry
from app.db import SessionLocal
from app.models.hive import Hive
from app.schemas.iot import HiveTelemetryCreate, HiveTelemetryResponse
from app.services.ai_cache import trigger_ai_analysis
from app.services.health_engine import HealthEngine

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IOT_SERVER_URL = settings.IOT_SERVER_URL
BACKEND_URL = settings.BACKEND_BASE_URL
POLL_INTERVAL_SECONDS = getattr(settings, "IOT_BRIDGE_POLL_SECONDS", 5)

# Cache: hive_id -> last state hash (to avoid duplicate processing and conserve CPU power)
_last_state_hash: Dict[int, str] = {}


def _state_hash(iot_data: dict) -> str:
    """Compute a hash of the IoT state to detect changes and conserve CPU."""
    key = (
        f"{iot_data.get('temperature')}-"
        f"{iot_data.get('humidity')}-"
        f"{iot_data.get('weight')}-"
        f"{iot_data.get('sound_level')}-"
        f"{iot_data.get('co2_level')}-"
        f"{iot_data.get('status')}-"
        f"{iot_data.get('last_updated')}"
    )
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def ingest_iot_data_entry(db, hive: Hive, iot_data: dict) -> Optional[HiveTelemetryResponse]:
    """
    Ingest a telemetry packet directly from IoT server data into the database pipeline.
    Runs HealthEngine evaluation, alert generation, WebSocket broadcast, and AI analysis.
    """
    try:
        temp = round(float(iot_data.get("temperature", 34.0)), 2)
        hum = round(float(iot_data.get("humidity", 60.0)), 2)
        weight = round(float(iot_data.get("weight", 25.0)), 2)
        sound = round(float(iot_data.get("sound_level", 50.0)), 2)
        co2 = float(iot_data.get("co2_level", 700.0))
        vibration_proxy = round(min(100.0, max(0.0, (co2 - 300.0) / 17.0 * (sound / 120.0))), 2)

        payload = HiveTelemetryCreate(
            temperature_c=Decimal(str(temp)),
            humidity_percent=Decimal(str(hum)),
            weight_kg=Decimal(str(weight)),
            sound_level=Decimal(str(sound)),
            vibration_level=Decimal(str(vibration_proxy)),
            battery_percent=None,
            timestamp=datetime.now(timezone.utc),
        )

        reading, is_dup = record_hive_telemetry(db, hive.id, payload, is_simulated=False)
        if is_dup:
            return HiveTelemetryResponse.model_validate(reading)

        # 1. Health Engine Evaluation & Anomaly Detection
        _, anomalies, alerts = HealthEngine.evaluate_telemetry(db, hive, reading)
        resp_model = HiveTelemetryResponse.model_validate(reading)

        # 2. WebSocket Broadcast for real-time live app updates
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                manager.broadcast_kvic("iot-update", hive.id, resp_model.model_dump(mode="json"))
            )
            for alert in alerts:
                loop.create_task(
                    manager.broadcast_kvic(
                        "alert",
                        hive.id,
                        {
                            "alert_type": alert.alert_type,
                            "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                            "message": alert.message,
                        },
                    )
                )
        except RuntimeError:
            pass  # No running event loop (e.g. called from synchronous test)

        # 3. Trigger Gemini AI Analysis if anomalies/alerts are present
        if anomalies or alerts:
            metrics_dict = {
                "temperature_c": temp,
                "humidity_percent": hum,
                "weight_kg": weight,
                "sound_level": sound,
                "vibration_level": vibration_proxy,
            }
            trigger_ai_analysis(
                hive_id=hive.id,
                hive_code=hive.hive_code,
                metrics=metrics_dict,
                anomalies=anomalies,
                is_simulated=False,
                background_tasks=None,
            )

        logger.info(
            "IoT Bridge: Ingested Hive %s (%s) from IoT server [temp=%.1f°C, hum=%.1f%%, weight=%.2fkg]",
            hive.id,
            hive.hive_code,
            temp,
            hum,
            weight,
        )
        return resp_model

    except TelemetryConflictError:
        return None
    except Exception as exc:
        logger.error("IoT Bridge: Error ingesting data for Hive %s: %s", getattr(hive, "id", "unknown"), exc)
        return None


async def sync_hive_from_iot(hive_id: int) -> Optional[dict]:
    """
    On-demand sync: fetches the latest state of a specific hive from the deployed IoT server
    and writes it directly to the database pipeline. Called on screen refresh.
    """
    async with httpx.AsyncClient() as client:
        try:
            iot_data = None
            # 1. Try single hive endpoint
            resp = await client.get(f"{IOT_SERVER_URL}/iot-data/{hive_id}", timeout=4)
            if resp.status_code == 200:
                payload = resp.json()
                entry = payload.get("data", {})
                iot_data = entry.get("data", entry)

            # 2. Fallback to all hives endpoint if single hive didn't return data
            if not iot_data:
                resp2 = await client.get(f"{IOT_SERVER_URL}/iot-data", timeout=4)
                if resp2.status_code == 200:
                    payload2 = resp2.json()
                    for entry in payload2.get("data", []):
                        if str(entry.get("hiveId")) == str(hive_id):
                            iot_data = entry.get("data", {})
                            break

            if not iot_data:
                return None

            current_hash = _state_hash(iot_data)
            if _last_state_hash.get(hive_id) == current_hash:
                # Telemetry hasn't changed on the IoT server; return without duplicate DB write
                return iot_data

            db = SessionLocal()
            try:
                hive = db.query(Hive).filter(Hive.id == hive_id).first()
                if hive:
                    ingest_iot_data_entry(db, hive, iot_data)
                    _last_state_hash[hive.id] = current_hash
                    return iot_data
            finally:
                db.close()
        except Exception as e:
            logger.warning("IoT Bridge: On-demand sync for Hive %s failed: %s", hive_id, e)
    return None


async def _poll_and_forward(client: httpx.AsyncClient):
    """
    Single poll cycle: fetch all hive states from the deployed IoT server
    and ingest changed ones directly into the database.
    """
    try:
        resp = await client.get(f"{IOT_SERVER_URL}/iot-data", timeout=5)
        if resp.status_code != 200:
            logger.warning("IoT Bridge: IoT server returned HTTP %s", resp.status_code)
            return
        payload = resp.json()
    except Exception as e:
        logger.warning("IoT Bridge: Unable to reach IoT server (%s): %s", IOT_SERVER_URL, e)
        return

    hive_entries = payload.get("data", [])
    if not hive_entries:
        return

    db = SessionLocal()
    try:
        for entry in hive_entries:
            h_id = entry.get("hiveId")
            iot_data = entry.get("data", {})
            if not h_id or not iot_data:
                continue

            current_hash = _state_hash(iot_data)
            try:
                h_id_int = int(h_id)
            except (ValueError, TypeError):
                h_id_int = None

            # Skip if unchanged to conserve low computer power
            if h_id_int and _last_state_hash.get(h_id_int) == current_hash:
                continue

            # Look up hive in database
            hive = None
            if h_id_int:
                hive = db.query(Hive).filter(Hive.id == h_id_int).first()
            if not hive:
                hive = db.query(Hive).filter(Hive.hive_code == iot_data.get("hive_code")).first()
            if not hive:
                continue

            if _last_state_hash.get(hive.id) == current_hash:
                continue

            _last_state_hash[hive.id] = current_hash
            ingest_iot_data_entry(db, hive, iot_data)

    except Exception as exc:
        logger.error("IoT Bridge: Error in poll cycle: %s", exc)
    finally:
        db.close()


async def run_iot_bridge():
    """
    Continuous background loop polling deployed IoT server every ~5 seconds.
    Lightweight, low CPU overhead, skips unchanged hives.
    """
    logger.info(
        "IoT Bridge: Starting background service. Polling %s every %ss -> DB",
        IOT_SERVER_URL,
        POLL_INTERVAL_SECONDS,
    )

    async with httpx.AsyncClient() as client:
        while True:
            try:
                await _poll_and_forward(client)
            except Exception as exc:
                logger.error("IoT Bridge: Unexpected error in background loop: %s", exc)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
