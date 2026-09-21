"""
IoT Bridge Sync Route — Honey Chain / Madhu Sathi

Exposes endpoints to sync data from the deployed IoT server into the backend:
  POST /bridge/sync            — manually trigger a sync cycle from IoT server
  POST /bridge/sync?hive_id=1  — sync a specific hive
  POST /bridge/webhook         — called by IoT server on state update
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Query, status
from fastapi.responses import JSONResponse

from app.db import SessionLocal
from app.models.hive import Hive
from app.services.iot_bridge import (
    IOT_SERVER_URL,
    _last_state_hash,
    _state_hash,
    ingest_iot_data_entry,
    sync_hive_from_iot,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bridge", tags=["IoT Bridge"])


async def _sync_hives(hive_id: Optional[int] = None) -> dict:
    """Core sync logic: fetch from deployed IoT server and ingest directly into database."""
    results = {"synced": [], "skipped_unchanged": [], "errors": []}

    async with httpx.AsyncClient() as client:
        try:
            url = f"{IOT_SERVER_URL}/iot-data" if not hive_id else f"{IOT_SERVER_URL}/iot-data/{hive_id}"
            resp = await client.get(url, timeout=8)
            if resp.status_code != 200:
                return {"error": f"IoT server returned HTTP {resp.status_code}"}
            payload = resp.json()
        except Exception as e:
            return {"error": f"IoT server unreachable: {e}"}

        if hive_id:
            entry = payload.get("data", {})
            hive_entries = [entry] if entry else []
        else:
            hive_entries = payload.get("data", [])

        db = SessionLocal()
        try:
            for item in hive_entries:
                h_id = item.get("hiveId") or item.get("hive_id")
                iot_data = item.get("data", item)
                if not h_id or not iot_data:
                    continue

                try:
                    h_int = int(h_id)
                except (ValueError, TypeError):
                    continue

                # Look up hive
                hive = db.query(Hive).filter(Hive.id == h_int).first()
                if not hive and iot_data.get("hive_code"):
                    hive = db.query(Hive).filter(Hive.hive_code == iot_data.get("hive_code")).first()

                if not hive:
                    results["errors"].append({"hive_id": h_int, "error": "Hive not found in database"})
                    continue

                current_hash = _state_hash(iot_data)
                _last_state_hash[hive.id] = current_hash

                res = ingest_iot_data_entry(db, hive, iot_data)
                if res:
                    results["synced"].append({
                        "hive_id": hive.id,
                        "hive_code": hive.hive_code,
                        "temperature_c": float(res.temperature_c),
                        "humidity_percent": float(res.humidity_percent),
                        "weight_kg": float(res.weight_kg),
                    })
                else:
                    results["skipped_unchanged"].append(hive.id)

        finally:
            db.close()

    return results


@router.post("/sync", summary="Sync deployed IoT server data directly into backend database")
async def sync_iot_to_backend(
    background_tasks: BackgroundTasks,
    hive_id: Optional[int] = Query(None, description="Sync a specific hive only (omit for all hives)"),
):
    """
    Polls the deployed IoT Mock Server and writes real telemetry into the backend pipeline.
    """
    results = await _sync_hives(hive_id=hive_id)
    logger.info("IoT Bridge manual sync: %s", results)
    return JSONResponse(content={"success": True, "results": results})


@router.post(
    "/webhook",
    summary="IoT server webhook — called by IoT server on state change",
)
async def iot_webhook(payload: dict):
    """
    Webhook endpoint called by IoT server on slider/scenario update.
    Immediately updates the hive in the backend DB and broadcasts to clients.
    """
    hive_id = payload.get("hiveId") or payload.get("hive_id")
    iot_data = payload.get("data", {})

    if not hive_id or not iot_data:
        return JSONResponse(
            content={"success": False, "error": "Missing hiveId or data"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    db = SessionLocal()
    try:
        hive = db.query(Hive).filter(Hive.id == int(hive_id)).first()
        if not hive and iot_data.get("hive_code"):
            hive = db.query(Hive).filter(Hive.hive_code == iot_data.get("hive_code")).first()

        if not hive:
            return JSONResponse(
                content={"success": False, "error": f"Hive {hive_id} not found in backend DB"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        res = ingest_iot_data_entry(db, hive, iot_data)
        if res:
            _last_state_hash[hive.id] = _state_hash(iot_data)
            return {
                "success": True,
                "hive_id": hive.id,
                "temperature_c": float(res.temperature_c),
                "status": "ingested",
            }
        return {"success": True, "hive_id": hive.id, "status": "duplicate_skipped"}

    finally:
        db.close()
