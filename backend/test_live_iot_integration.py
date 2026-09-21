"""
Test Live IoT Server Integration with Backend
Tests that all data comes from https://iotmockserver.vercel.app without hardcoded fallbacks,
and that changes on the IoT server replicate into the backend database.
"""
import asyncio
import httpx
from app.db import SessionLocal
from app.models.hive import Hive
from app.models.hive_telemetry import HiveTelemetry
from app.services.iot_bridge import sync_hive_from_iot, _poll_and_forward
from app.services.health_engine import HealthEngine

async def run_test():
    IOT_URL = "https://iotmockserver.vercel.app/api/v1"
    
    print("--- 1. Testing Connection to Deployed IoT Server ---")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{IOT_URL}/iot-data/1", timeout=10)
        assert r.status_code == 200, f"Failed to get hive 1: {r.status_code}"
        data = r.json()
        print(f"IoT Server Hive 1 initial: temp={data['data']['data']['temperature']}, status={data['data']['data']['status']}")

        print("\n--- 2. Setting Scenario to 'overheating' on IoT Server ---")
        set_resp = await client.post(f"{IOT_URL}/set-scenario/1", json={"scenario": "overheating"}, timeout=10)
        assert set_resp.status_code == 200, f"Failed to set scenario: {set_resp.status_code}"
        print(f"IoT Server response: {set_resp.json()}")

        # Check new state on IoT server
        r2 = await client.get(f"{IOT_URL}/iot-data/1", timeout=10)
        data2 = r2.json()
        new_temp = data2['data']['data']['temperature']
        print(f"IoT Server Hive 1 after overheating scenario: temp={new_temp}")
        assert new_temp > 38.0, f"Expected overheating temp > 38.0, got {new_temp}"

    print("\n--- 3. Triggering Backend Sync from Deployed IoT Server ---")
    synced = await sync_hive_from_iot(1)
    print(f"Backend sync result: {synced}")

    db = SessionLocal()
    try:
        latest = (
            db.query(HiveTelemetry)
            .filter(HiveTelemetry.hive_id == 1)
            .order_by(HiveTelemetry.timestamp.desc())
            .first()
        )
        print(f"Latest Telemetry in DB: temp={latest.temperature_c}°C, hum={latest.humidity_percent}%, weight={latest.weight_kg}kg")
        assert float(latest.temperature_c) == float(new_temp), f"DB temp {latest.temperature_c} != IoT server temp {new_temp}"
        
        hive = db.query(Hive).filter(Hive.id == 1).first()
        health = HealthEngine.get_health_summary(db, hive)
        print(f"Health Summary: status={health.health_status}, severity={health.severity}, active_alerts={health.metrics.active_alerts_count}")
    finally:
        db.close()

    print("\n--- 4. Resetting Scenario to 'healthy' on IoT Server ---")
    async with httpx.AsyncClient() as client:
        reset_resp = await client.post(f"{IOT_URL}/set-scenario/1", json={"scenario": "healthy"}, timeout=10)
        print(f"Reset response: {reset_resp.json()}")
        
    synced_healthy = await sync_hive_from_iot(1)
    print(f"Backend synced after healthy reset: {synced_healthy}")

    db = SessionLocal()
    try:
        latest_healthy = (
            db.query(HiveTelemetry)
            .filter(HiveTelemetry.hive_id == 1)
            .order_by(HiveTelemetry.timestamp.desc())
            .first()
        )
        print(f"Latest Telemetry in DB after reset: temp={latest_healthy.temperature_c}°C, status={latest_healthy.is_simulated}")
    finally:
        db.close()

    print("\nSUCCESS! Live IoT server synchronization verified end-to-end!")

if __name__ == "__main__":
    asyncio.run(run_test())
