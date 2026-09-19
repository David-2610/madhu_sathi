"""
IoT Bridge Sync Route — Honey Chain

Exposes a single HTTP endpoint that, when called, immediately polls the IoT
Mock Server and forwards any changed telemetry to the backend pipeline.

Usage:
  POST /bridge/sync          — trigger one manual sync cycle
  POST /bridge/sync?hive_id=3  — sync a specific hive only

This endpoint is designed to be called:
  1. By the IoT Mock Server's webhook on every state change (automatic)
  2. By a Vercel Cron job every 30 seconds (scheduled)
  3. Manually for testing

This solves the Vercel serverless limitation where background asyncio tasks
don't persist between requests.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from app.services.iot_bridge import (
    BACKEND_URL,
    IOT_SERVER_URL,
    TRACKED_HIVE_IDS,
    _get_auth_token,
    _invalidate_token,
    _last_state_hash,
    _map_iot_to_telemetry,
    _state_hash,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bridge", tags=["IoT Bridge"])


async def _sync_hives(hive_id: Optional[int] = None) -> dict:
    """Core sync logic: poll IoT server, forward changed telemetry to backend."""
    results = {"synced": [], "skipped_unchanged": [], "errors": []}

    async with httpx.AsyncClient() as client:
        # 1. Fetch IoT data
        try:
            resp = await client.get(f"{IOT_SERVER_URL}/iot-data", timeout=10)
            if resp.status_code != 200:
                return {"error": f"IoT server returned {resp.status_code}"}
            hive_entries = resp.json().get("data", [])
        except Exception as e:
            return {"error": f"IoT server unreachable: {e}"}

        # 2. Get auth token
        token = await _get_auth_token(client)
        if not token:
            return {"error": "Backend authentication failed"}

        # 3. Filter hives if specific hive_id requested
        if hive_id:
            hive_entries = [e for e in hive_entries if e.get("hiveId") == hive_id]

        # 4. Forward each changed hive
        for entry in hive_entries:
            h_id = entry.get("hiveId")
            iot_data = entry.get("data", {})

            if h_id not in TRACKED_HIVE_IDS:
                continue

            current_hash = _state_hash(iot_data)
            if _last_state_hash.get(h_id) == current_hash:
                results["skipped_unchanged"].append(h_id)
                continue

            _last_state_hash[h_id] = current_hash
            telemetry = _map_iot_to_telemetry(iot_data)

            try:
                post_resp = await client.post(
                    f"{BACKEND_URL}/beekeeper/hives/{h_id}/telemetry",
                    json=telemetry,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15,
                )

                if post_resp.status_code in (200, 201):
                    results["synced"].append({
                        "hive_id": h_id,
                        "temperature_c": telemetry["temperature_c"],
                        "status": post_resp.status_code,
                    })
                elif post_resp.status_code == 409:
                    # Duplicate — treat as skipped
                    results["skipped_unchanged"].append(h_id)
                elif post_resp.status_code == 401:
                    _invalidate_token()
                    results["errors"].append({"hive_id": h_id, "error": "Token expired, will retry"})
                else:
                    results["errors"].append({
                        "hive_id": h_id,
                        "error": f"Backend returned {post_resp.status_code}",
                    })
            except Exception as e:
                results["errors"].append({"hive_id": h_id, "error": str(e)})

    return results


@router.post("/sync", summary="Sync IoT server data into backend telemetry pipeline")
async def sync_iot_to_backend(
    background_tasks: BackgroundTasks,
    hive_id: Optional[int] = Query(None, description="Sync a specific hive only (omit for all hives)"),
):
    """
    Polls the IoT Mock Server and forwards changed telemetry to the backend pipeline.

    Data flow triggered:
      IoT Server → Backend → Health Engine → Alerts → WebSocket → Frontend
    """
    results = await _sync_hives(hive_id=hive_id)
    logger.info("IoT Bridge sync: %s", results)
    return JSONResponse(content={"success": True, "results": results})


@router.post(
    "/webhook",
    summary="IoT server webhook — called by IoT server on state change",
)
async def iot_webhook(payload: dict):
    """
    Webhook endpoint that the IoT Mock Server can call after updating a hive.
    Immediately forwards the new state to the backend's telemetry pipeline.

    Expected payload from IoT server:
      { "hiveId": 3, "data": { "temperature": 42, "humidity": 55, ... } }
    """
    hive_id = payload.get("hiveId")
    iot_data = payload.get("data", {})

    if not hive_id or not iot_data:
        return JSONResponse(content={"success": False, "error": "Missing hiveId or data"}, status_code=400)

    async with httpx.AsyncClient() as client:
        token = await _get_auth_token(client)
        if not token:
            return JSONResponse(content={"success": False, "error": "Auth failed"}, status_code=500)

        telemetry = _map_iot_to_telemetry(iot_data)
        post_resp = await client.post(
            f"{BACKEND_URL}/beekeeper/hives/{hive_id}/telemetry",
            json=telemetry,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )

    if post_resp.status_code in (200, 201, 409):
        return {"success": True, "hive_id": hive_id, "backend_status": post_resp.status_code}
    else:
        return JSONResponse(
            content={"success": False, "backend_status": post_resp.status_code, "detail": post_resp.text[:200]},
            status_code=502,
        )
