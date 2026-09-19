"""
IoT Bridge Service — Honey Chain

Bridges the IoT Mock Server with the main FastAPI backend.

Data Flow:
  IoT Mock Server (https://iotmockserver.vercel.app)
    → polls every N seconds via REST
    → forwards telemetry to POST /beekeeper/hives/{hive_id}/telemetry
    → backend triggers health evaluation, alerts, and WebSocket broadcast
    → Frontend (Android app) receives updates via WebSocket

This service runs as a FastAPI background task on startup (in non-test envs).
It does NOT change the IoT server structure — it simply reads from it
and writes into the main backend's telemetry pipeline.
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IOT_SERVER_URL = settings.IOT_SERVER_URL
BACKEND_URL = settings.BACKEND_BASE_URL
POLL_INTERVAL_SECONDS = settings.IOT_BRIDGE_POLL_SECONDS

# These are the hive IDs managed by the IoT Mock Server that mirror backend hive IDs
TRACKED_HIVE_IDS = [1, 2, 3, 4, 5]

# Cache: hive_id -> last state hash (to avoid forwarding duplicate readings)
_last_state_hash: dict[int, str] = {}

# Cache: beekeeper JWT token + expiry
_cached_token: Optional[str] = None

# Beekeeper credentials used by the bridge (test2 = BEEKEEPER role)
BRIDGE_EMAIL = "test2@gamil.com"
BRIDGE_PASSWORD = "test1234"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
async def _get_auth_token(client: httpx.AsyncClient) -> str:
    """Retrieve a fresh JWT from the backend for the bridge beekeeper account."""
    global _cached_token
    if _cached_token:
        return _cached_token

    logger.info("IoT Bridge: Authenticating with backend...")
    try:
        resp = await client.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": BRIDGE_EMAIL, "password": BRIDGE_PASSWORD},
            timeout=15,
        )
        if resp.status_code == 200:
            _cached_token = resp.json()["access_token"]
            logger.info("IoT Bridge: Authenticated successfully.")
            return _cached_token
        else:
            logger.error("IoT Bridge: Auth failed %s %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("IoT Bridge: Auth error: %s", e)
    return ""


def _invalidate_token():
    """Force re-authentication on next cycle."""
    global _cached_token
    _cached_token = None


# ---------------------------------------------------------------------------
# Field mapping: IoT server → backend telemetry schema
# ---------------------------------------------------------------------------
def _map_iot_to_telemetry(iot_data: dict) -> dict:
    """
    Map IoT Mock Server fields to the backend's HiveTelemetryCreate schema.

    IoT Server fields:
      temperature, humidity, weight, sound_level, co2_level

    Backend expects:
      temperature_c, humidity_percent, weight_kg, sound_level, vibration_level
    """
    # Derive a vibration_level from sound_level + co2_level as a proxy
    # (IoT server doesn't have vibration; we derive it from co2 anomaly)
    co2 = float(iot_data.get("co2_level", 700))
    sound = float(iot_data.get("sound_level", 50))
    vibration_proxy = round(min(100, (co2 - 300) / 17.0 * (sound / 120)), 2)

    return {
        "temperature_c": round(float(iot_data.get("temperature", 34)), 2),
        "humidity_percent": round(float(iot_data.get("humidity", 60)), 2),
        "weight_kg": round(float(iot_data.get("weight", 25)), 2),
        "sound_level": round(sound, 2),
        "vibration_level": vibration_proxy,
        "battery_percent": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _state_hash(iot_data: dict) -> str:
    """Compute a simple hash of the IoT state to detect changes."""
    key = f"{iot_data.get('temperature')}-{iot_data.get('humidity')}-{iot_data.get('weight')}-{iot_data.get('sound_level')}-{iot_data.get('co2_level')}"
    return hashlib.md5(key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Core polling loop
# ---------------------------------------------------------------------------
async def _poll_and_forward(client: httpx.AsyncClient):
    """Single poll cycle: fetch all hive states from IoT server and forward changed ones."""
    # 1. Fetch all IoT hive states
    try:
        resp = await client.get(f"{IOT_SERVER_URL}/iot-data", timeout=10)
        if resp.status_code != 200:
            logger.warning("IoT Bridge: IoT server returned %s", resp.status_code)
            return
        payload = resp.json()
    except Exception as e:
        logger.warning("IoT Bridge: Failed to reach IoT server: %s", e)
        return

    hive_entries = payload.get("data", [])

    # 2. Get auth token once per cycle
    token = await _get_auth_token(client)
    if not token:
        return

    # 3. For each hive, if state changed, forward to backend
    for entry in hive_entries:
        hive_id = entry.get("hiveId")
        iot_data = entry.get("data", {})

        if hive_id not in TRACKED_HIVE_IDS:
            continue

        current_hash = _state_hash(iot_data)
        if _last_state_hash.get(hive_id) == current_hash:
            continue  # No change since last poll — skip

        _last_state_hash[hive_id] = current_hash

        telemetry = _map_iot_to_telemetry(iot_data)

        try:
            post_resp = await client.post(
                f"{BACKEND_URL}/beekeeper/hives/{hive_id}/telemetry",
                json=telemetry,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )

            if post_resp.status_code in (200, 201):
                logger.info(
                    "IoT Bridge: Forwarded hive %s telemetry (temp=%.1f°C) → backend ✓",
                    hive_id,
                    telemetry["temperature_c"],
                )
            elif post_resp.status_code == 409:
                # Duplicate timestamp — not a real error
                logger.debug("IoT Bridge: Duplicate telemetry for hive %s, skipped.", hive_id)
            elif post_resp.status_code == 401:
                logger.warning("IoT Bridge: Token expired, re-authenticating...")
                _invalidate_token()
                break  # Retry next cycle with fresh token
            else:
                logger.warning(
                    "IoT Bridge: Backend rejected hive %s telemetry: %s %s",
                    hive_id,
                    post_resp.status_code,
                    post_resp.text[:200],
                )

        except Exception as e:
            logger.error("IoT Bridge: Error forwarding hive %s: %s", hive_id, e)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
async def run_iot_bridge():
    """
    Main loop. Runs as a background asyncio task.
    Call this from the FastAPI lifespan startup.
    """
    logger.info(
        "IoT Bridge: Starting. Polling %s every %ss → %s",
        IOT_SERVER_URL,
        POLL_INTERVAL_SECONDS,
        BACKEND_URL,
    )

    async with httpx.AsyncClient() as client:
        while True:
            try:
                await _poll_and_forward(client)
            except Exception as e:
                logger.error("IoT Bridge: Unexpected error in poll cycle: %s", e)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
