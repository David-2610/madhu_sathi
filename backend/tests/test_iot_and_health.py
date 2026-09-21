"""
Comprehensive test suite for Phase 7:
IoT Devices, Telemetry, Hive Health Engine, Alerts, AI Assistance & Simulator.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal, check_db_connection
from app.main import app
from app.models.apiary import Apiary
from app.models.beekeeper import BeekeeperProfile
from app.models.hive import Hive, HiveStatus
from app.models.hive_alert import AlertSeverity, AlertStatus, AlertType, HiveAlert
from app.models.hive_device import HiveDevice
from app.models.hive_telemetry import HiveTelemetry
from app.models.user import User
from app.schemas.iot import SimulatorScenario
from app.services.ai.base import AIProvider
from app.services.mqtt import get_mqtt_provider

client = TestClient(app)

skip_if_no_db = pytest.mark.skipif(
    not check_db_connection(),
    reason="Database is not reachable — skipping DB-dependent tests",
)


# ── Cleanup Helper ─────────────────────────────────────────────────────────
def _cleanup_user_hierarchy(email: str) -> None:
    """Safely delete a user and all child IoT and beekeeping records."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return
        profile = db.query(BeekeeperProfile).filter(BeekeeperProfile.user_id == user.id).first()
        if profile:
            apiary_ids = [a[0] for a in db.query(Apiary.id).filter(Apiary.beekeeper_id == profile.id).all()]
            if apiary_ids:
                hive_ids = [h[0] for h in db.query(Hive.id).filter(Hive.apiary_id.in_(apiary_ids)).all()]
                if hive_ids:
                    db.query(HiveAlert).filter(HiveAlert.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(HiveTelemetry).filter(HiveTelemetry.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(HiveDevice).filter(HiveDevice.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(Hive).filter(Hive.id.in_(hive_ids)).delete(synchronize_session=False)
                db.query(Apiary).filter(Apiary.id.in_(apiary_ids)).delete(synchronize_session=False)
            db.query(BeekeeperProfile).filter(BeekeeperProfile.id == profile.id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_user_and_token(email: str, role: str, phone: str = "9870000001") -> Tuple[dict, str]:
    password = "SecurePassword123"
    register_payload = {
        "full_name": f"Test {role.title()}",
        "email": email,
        "phone": phone,
        "password": password,
        "role": role,
    }
    r = client.post("/auth/register", json=register_payload)
    if r.status_code == 409:
        pass
    login_payload = {"email": email, "password": password}
    resp = client.post("/auth/login", json=login_payload)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    user = resp.json()["user"]
    return user, token


def _setup_beekeeper_hive(email: str, phone: str = "9870000002") -> Tuple[str, int, int]:
    """Helper creating beekeeper profile, apiary, and hive. Returns (token, apiary_id, hive_id)."""
    _cleanup_user_hierarchy(email)
    _, token = _create_user_and_token(email, "BEEKEEPER", phone)
    headers = _auth_header(token)

    # 1. Profile
    p_resp = client.post("/beekeeper/profile", json={
        "beekeeper_code": f"BK-{email.split('@')[0]}",
        "state": "Uttarakhand",
        "district": "Nainital",
        "experience_years": 4,
    }, headers=headers)
    assert p_resp.status_code == 201

    # 2. Apiary
    a_resp = client.post("/beekeeper/apiaries", json={
        "name": "Mountain Valley Apiary",
        "location_name": "Valley Site",
        "latitude": 29.38,
        "longitude": 79.45,
    }, headers=headers)
    assert a_resp.status_code == 201
    apiary_id = a_resp.json()["id"]

    # 3. Hive
    h_resp = client.post(f"/beekeeper/apiaries/{apiary_id}/hives", json={
        "hive_code": "HIVE-01",
        "hive_type": "LANGSTROTH",
    }, headers=headers)
    assert h_resp.status_code == 201
    hive_id = h_resp.json()["id"]

    return token, apiary_id, hive_id


# ── Tests ──────────────────────────────────────────────────────────────────
@skip_if_no_db
def test_telemetry_physical_bounds_validation():
    """Verify impossible physical values are rejected with HTTP 422."""
    email = "iot_bounds@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Impossible temperature (120°C)
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 120.0,
            "humidity_percent": 50.0,
            "weight_kg": 25.0,
            "sound_level": 40.0,
            "vibration_level": 1.0,
        }, headers=headers)
        assert resp.status_code == 422

        # Impossible temperature (-50°C)
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": -50.0,
            "humidity_percent": 50.0,
            "weight_kg": 25.0,
            "sound_level": 40.0,
            "vibration_level": 1.0,
        }, headers=headers)
        assert resp.status_code == 422

        # Impossible humidity (150%)
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 34.0,
            "humidity_percent": 150.0,
            "weight_kg": 25.0,
            "sound_level": 40.0,
            "vibration_level": 1.0,
        }, headers=headers)
        assert resp.status_code == 422

        # Negative weight (-5 kg)
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 34.0,
            "humidity_percent": 50.0,
            "weight_kg": -5.0,
            "sound_level": 40.0,
            "vibration_level": 1.0,
        }, headers=headers)
        assert resp.status_code == 422

        # Negative sound level (-10 dB)
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 34.0,
            "humidity_percent": 50.0,
            "weight_kg": 25.0,
            "sound_level": -10.0,
            "vibration_level": 1.0,
        }, headers=headers)
        assert resp.status_code == 422
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_device_registration_lifecycle_and_uniqueness():
    """Verify device registration, uniqueness, and listing."""
    email = "iot_device@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Register device
        resp = client.post(f"/beekeeper/hives/{hive_id}/devices", json={
            "device_id": "ESP32-NODE-UK-01",
            "device_type": "ESP32_LORA",
            "firmware_version": "v1.0.4",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["device_id"] == "ESP32-NODE-UK-01"
        assert data["hive_id"] == hive_id
        assert data["is_active"] is True

        # Duplicate registration fails with HTTP 409
        dup_resp = client.post(f"/beekeeper/hives/{hive_id}/devices", json={
            "device_id": "ESP32-NODE-UK-01",
        }, headers=headers)
        assert dup_resp.status_code == 409

        # List devices
        list_resp = client.get(f"/beekeeper/hives/{hive_id}/devices", headers=headers)
        assert list_resp.status_code == 200
        devices = list_resp.json()
        assert len(devices) == 1
        assert devices[0]["device_id"] == "ESP32-NODE-UK-01"
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_cross_beekeeper_isolation_for_iot():
    """Verify Beekeeper B cannot access Beekeeper A's devices, telemetry, or alerts (HTTP 404)."""
    email_a = "bk_iot_a@example.com"
    email_b = "bk_iot_b@example.com"
    token_a, _, hive_a_id = _setup_beekeeper_hive(email_a, phone="9870000003")
    token_b, _, hive_b_id = _setup_beekeeper_hive(email_b, phone="9870000004")

    headers_b = _auth_header(token_b)

    try:
        # B cannot register device to A's hive
        r1 = client.post(f"/beekeeper/hives/{hive_a_id}/devices", json={
            "device_id": "INTRUDER-NODE-01",
        }, headers=headers_b)
        assert r1.status_code == 404

        # B cannot view devices of A's hive
        r2 = client.get(f"/beekeeper/hives/{hive_a_id}/devices", headers=headers_b)
        assert r2.status_code == 404

        # B cannot post telemetry to A's hive
        r3 = client.post(f"/beekeeper/hives/{hive_a_id}/telemetry", json={
            "temperature_c": 34.5,
            "humidity_percent": 60.0,
            "weight_kg": 25.0,
            "sound_level": 45.0,
            "vibration_level": 0.5,
        }, headers=headers_b)
        assert r3.status_code == 404

        # B cannot view telemetry of A's hive
        r4 = client.get(f"/beekeeper/hives/{hive_a_id}/telemetry", headers=headers_b)
        assert r4.status_code == 404

        # B cannot view health of A's hive
        r5 = client.get(f"/beekeeper/hives/{hive_a_id}/health", headers=headers_b)
        assert r5.status_code == 404

        # B cannot query assistant for A's hive
        r6 = client.post(f"/beekeeper/hives/{hive_a_id}/assistant", json={}, headers=headers_b)
        assert r6.status_code == 404
    finally:
        _cleanup_user_hierarchy(email_a)
        _cleanup_user_hierarchy(email_b)


@skip_if_no_db
def test_buyer_and_kvic_admin_cannot_access_iot_endpoints():
    """Verify non-beekeeper roles are rejected with HTTP 403."""
    email_bk = "bk_for_buyer_check@example.com"
    email_buyer = "buyer_iot_chk@example.com"
    _, _, hive_id = _setup_beekeeper_hive(email_bk, phone="9870000005")

    _cleanup_user_hierarchy(email_buyer)
    _, buyer_token = _create_user_and_token(email_buyer, "BUYER", phone="9870000006")
    buyer_headers = _auth_header(buyer_token)

    try:
        r1 = client.get(f"/beekeeper/hives/{hive_id}/devices", headers=buyer_headers)
        assert r1.status_code == 403

        r2 = client.get(f"/beekeeper/hives/{hive_id}/telemetry", headers=buyer_headers)
        assert r2.status_code == 403

        r3 = client.get(f"/beekeeper/hives/{hive_id}/health", headers=buyer_headers)
        assert r3.status_code == 403
    finally:
        _cleanup_user_hierarchy(email_bk)
        _cleanup_user_hierarchy(email_buyer)


@skip_if_no_db
def test_normal_telemetry_ingestion_and_mqtt_dispatch():
    """Verify normal telemetry ingestion, MQTT message publishing, and healthy status."""
    email = "iot_normal@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    mqtt = get_mqtt_provider()
    initial_mqtt_count = len(getattr(mqtt, "message_history", []))

    try:
        # Ingest normal reading
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 34.50,
            "humidity_percent": 60.00,
            "weight_kg": 26.00,
            "sound_level": 42.00,
            "vibration_level": 0.50,
            "battery_percent": 96.00,
            "device_id": "NODE-NORM-1",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["temperature_c"] == "34.50"
        assert data["is_simulated"] is False

        # Verify MQTT published
        current_mqtt_count = len(getattr(mqtt, "message_history", []))
        assert current_mqtt_count > initial_mqtt_count

        # Check health summary
        h_resp = client.get(f"/beekeeper/hives/{hive_id}/health", headers=headers)
        assert h_resp.status_code == 200
        health = h_resp.json()
        assert health["health_status"] == "HEALTHY"
        assert health["severity"] == "NORMAL"
        assert len(health["active_alerts"]) == 0
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_high_temperature_anomaly_and_alert():
    """Verify high temperature anomaly produces CRITICAL alert with non-diagnostic wording."""
    email = "iot_hightemp@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Ingest critical high temp (42.5°C)
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 42.50,
            "humidity_percent": 55.00,
            "weight_kg": 25.00,
            "sound_level": 45.00,
            "vibration_level": 0.50,
        }, headers=headers)
        assert resp.status_code == 201

        # Check alerts
        a_resp = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers)
        assert a_resp.status_code == 200
        alerts = a_resp.json()
        assert len(alerts) >= 1
        high_temp_alert = next((a for a in alerts if a["alert_type"] == "HIGH_TEMPERATURE"), None)
        assert high_temp_alert is not None
        assert high_temp_alert["severity"] == "CRITICAL"
        assert "Possible abnormal hive condition detected" in high_temp_alert["title"]
        assert "Disease confirmed" not in high_temp_alert["message"]

        # Health status is CRITICAL
        h_resp = client.get(f"/beekeeper/hives/{hive_id}/health", headers=headers)
        assert h_resp.status_code == 200
        assert h_resp.json()["health_status"] == "CRITICAL"
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_rapid_weight_drop_anomaly():
    """Verify sudden weight drop produces RAPID_WEIGHT_DROP alert."""
    email = "iot_weightdrop@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Reading 1: Baseline weight (28.0 kg)
        now = datetime.now(timezone.utc)
        r1 = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "timestamp": (now - timedelta(minutes=15)).isoformat(),
            "temperature_c": 34.50,
            "humidity_percent": 60.00,
            "weight_kg": 28.00,
            "sound_level": 45.00,
            "vibration_level": 0.50,
        }, headers=headers)
        assert r1.status_code == 201

        # Reading 2: Weight drops by 2.5 kg (25.5 kg)
        r2 = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "timestamp": now.isoformat(),
            "temperature_c": 34.50,
            "humidity_percent": 60.00,
            "weight_kg": 25.50,
            "sound_level": 45.00,
            "vibration_level": 0.50,
        }, headers=headers)
        assert r2.status_code == 201

        # Check alerts
        a_resp = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers)
        assert a_resp.status_code == 200
        alerts = a_resp.json()
        weight_alert = next((a for a in alerts if a["alert_type"] == "RAPID_WEIGHT_DROP"), None)
        assert weight_alert is not None
        assert weight_alert["severity"] == "HIGH"
        assert "swarming" in weight_alert["message"].lower() or "weight" in weight_alert["message"].lower()
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_abnormal_sound_and_vibration_combined():
    """Verify loud sound + vibration generates COMBINED_ANOMALY alert."""
    email = "iot_agitation@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 35.00,
            "humidity_percent": 60.00,
            "weight_kg": 25.00,
            "sound_level": 82.00,       # > 75 dB
            "vibration_level": 5.50,    # > 4.0
        }, headers=headers)
        assert resp.status_code == 201

        a_resp = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers)
        assert a_resp.status_code == 200
        alerts = a_resp.json()
        assert len(alerts) >= 1
        combined = next((a for a in alerts if a["alert_type"] == "COMBINED_ANOMALY"), None)
        assert combined is not None
        assert combined["severity"] == "HIGH"
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_alert_deduplication_and_cooldown():
    """Verify multiple anomalous readings within cooldown window do not flood duplicate alerts."""
    email = "iot_dedup@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Ingest reading 1 triggering high temperature
        r1 = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 41.50,
            "humidity_percent": 50.00,
            "weight_kg": 25.00,
            "sound_level": 40.00,
            "vibration_level": 0.50,
        }, headers=headers)
        assert r1.status_code == 201

        # Check alert count
        a1 = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers).json()
        initial_alert_count = len(a1)
        assert initial_alert_count >= 1

        # Ingest reading 2 with high temperature again 1 minute later
        r2 = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 41.80,
            "humidity_percent": 50.00,
            "weight_kg": 25.00,
            "sound_level": 40.00,
            "vibration_level": 0.50,
        }, headers=headers)
        assert r2.status_code == 201

        # Alert count must NOT have increased because of deduplication cooldown
        a2 = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers).json()
        assert len(a2) == initial_alert_count
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_alert_lifecycle_acknowledge_and_resolve():
    """Verify alert transitions from OPEN -> ACKNOWLEDGED -> RESOLVED."""
    email = "iot_lifecycle@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Trigger alert with low humidity (20%)
        client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 34.00,
            "humidity_percent": 20.00,
            "weight_kg": 25.00,
            "sound_level": 40.00,
            "vibration_level": 0.50,
        }, headers=headers)

        alerts = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers).json()
        assert len(alerts) >= 1
        alert_id = alerts[0]["id"]
        assert alerts[0]["status"] == "OPEN"

        # 1. Acknowledge
        ack_resp = client.post(f"/beekeeper/alerts/{alert_id}/acknowledge", headers=headers)
        assert ack_resp.status_code == 200
        ack_data = ack_resp.json()
        assert ack_data["status"] == "ACKNOWLEDGED"
        assert ack_data["acknowledged_at"] is not None

        # 2. Resolve
        res_resp = client.post(f"/beekeeper/alerts/{alert_id}/resolve", headers=headers)
        assert res_resp.status_code == 200
        res_data = res_resp.json()
        assert res_data["status"] == "RESOLVED"
        assert res_data["resolved_at"] is not None
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_ai_assistant_explanation_and_recommendations():
    """Verify AI assistant returns structured explanation, actionable steps, and disclaimer."""
    email = "iot_ai@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Ingest reading with elevated temperature
        client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 38.50,
            "humidity_percent": 55.00,
            "weight_kg": 25.00,
            "sound_level": 45.00,
            "vibration_level": 0.50,
        }, headers=headers)

        # Call AI assistant
        resp = client.post(f"/beekeeper/hives/{hive_id}/assistant", json={
            "query": "Is my hive overheating?",
        }, headers=headers)
        assert resp.status_code == 200
        ai = resp.json()
        assert isinstance(ai["is_mock"], bool)
        assert ai["provider"] in ("MOCK_AI", "GEMINI_AI")
        assert len(ai["recommended_steps"]) > 0
        assert "Possible abnormal hive condition detected" in ai["disclaimer"]
        assert "Disease confirmed" not in ai["explanation"]
        assert "Disease confirmed" not in ai["disclaimer"]
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_iot_simulator_scenarios():
    """Verify IoT simulator runs various scenarios and marks data is_simulated=True."""
    email = "iot_sim@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Scenario 1: HIGH_TEMPERATURE
        r1 = client.post(f"/beekeeper/hives/{hive_id}/simulator/run", json={
            "scenario": SimulatorScenario.HIGH_TEMPERATURE.value,
        }, headers=headers)
        assert r1.status_code == 201
        data1 = r1.json()
        assert data1["telemetry"]["is_simulated"] is True
        assert float(data1["telemetry"]["temperature_c"]) >= 41.0
        assert data1["health_status"] == "CRITICAL"

        # Scenario 2: NORMAL
        r2 = client.post(f"/beekeeper/hives/{hive_id}/simulator/run", json={
            "scenario": SimulatorScenario.NORMAL.value,
        }, headers=headers)
        assert r2.status_code == 201
        data2 = r2.json()
        assert data2["telemetry"]["is_simulated"] is True
        assert float(data2["telemetry"]["temperature_c"]) == 34.50
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_low_humidity_anomaly_and_alert():
    """Verify low humidity generates LOW_HUMIDITY alert with MEDIUM severity."""
    email = "iot_lowhum@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "temperature_c": 34.50,
            "humidity_percent": 22.00,  # Below 40%
            "weight_kg": 25.00,
            "sound_level": 40.00,
            "vibration_level": 0.50,
        }, headers=headers)
        assert resp.status_code == 201

        a_resp = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers)
        assert a_resp.status_code == 200
        alerts = a_resp.json()
        hum_alert = next((a for a in alerts if a["alert_type"] == "LOW_HUMIDITY"), None)
        assert hum_alert is not None
        assert hum_alert["severity"] == "MEDIUM"
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_missing_stale_telemetry_detection():
    """Verify health engine detects stale telemetry exceeding timeout window."""
    email = "iot_stale@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    try:
        # Ingest reading timestamped 3 hours in the past
        past_time = datetime.now(timezone.utc) - timedelta(hours=3)
        resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", json={
            "timestamp": past_time.isoformat(),
            "temperature_c": 34.50,
            "humidity_percent": 60.00,
            "weight_kg": 25.00,
            "sound_level": 40.00,
            "vibration_level": 0.50,
        }, headers=headers)
        assert resp.status_code == 201

        # Check health summary
        h_resp = client.get(f"/beekeeper/hives/{hive_id}/health", headers=headers)
        assert h_resp.status_code == 200
        health = h_resp.json()
        assert "MISSING_TELEMETRY" in health["anomalies"]
        assert health["health_status"] in ("NEEDS_ATTENTION", "CRITICAL")
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_ai_assistant_safe_fallback(monkeypatch):
    """Verify that if AI provider encounters an error, backend returns graceful fallback."""
    email = "iot_aifallback@example.com"
    token, _, hive_id = _setup_beekeeper_hive(email)
    headers = _auth_header(token)

    from app.services.ai.gemini_provider import GeminiAIProvider

    def buggy_call(*args, **kwargs):
        raise RuntimeError("External network connection timeout")

    monkeypatch.setattr(GeminiAIProvider, "generate_explanation", buggy_call)

    try:
        resp = client.post(f"/beekeeper/hives/{hive_id}/assistant", json={
            "query": "What should I do about the bees?",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["explanation"] is not None
        assert len(data["recommended_steps"]) > 0
    finally:
        _cleanup_user_hierarchy(email)

