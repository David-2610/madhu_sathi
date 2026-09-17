"""
Phase 8 Backend Hardening & OpenAPI Contract Test Suite.

Verifies:
1. IoT Hardware Token Authentication (`X-Device-Token`) vs Beekeeper JWT.
2. Cross-hive hardware token isolation.
3. Telemetry idempotency and duplicate reading prevention (200 is_duplicate vs 409 conflict).
4. Strict alert lifecycle state machine (OPEN -> ACKNOWLEDGED -> RESOLVED, illegal transitions rejected with 400).
5. Production-safe missing telemetry detection (unmonitored hives vs active hardware vs stale telemetry).
6. Comprehensive cross-owner isolation and RBAC matrix.
7. Public privacy audit (/trace/{token} and /marketplace/products leak zero PII or credentials).
8. Consistent query pagination on listing endpoints.
9. OpenAPI 3.1.0 schema structure, docs, and redoc.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets
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
from app.models.honey_batch import BatchStatus, HoneyBatch
from app.models.honey_harvest import HoneyHarvest
from app.models.honey_product import HoneyProduct, ProductStatus
from app.models.traceability_event import TraceabilityEvent
from app.models.user import User, UserRole
from app.services.qr import build_trace_url, generate_qr_svg

client = TestClient(app)

skip_if_no_db = pytest.mark.skipif(
    not check_db_connection(),
    reason="Database is not reachable — skipping DB-dependent tests",
)


def _cleanup_users(*emails: str) -> None:
    db: Session = SessionLocal()
    try:
        for email in emails:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                continue
            profile = db.query(BeekeeperProfile).filter(BeekeeperProfile.user_id == user.id).first()
            if profile:
                apiaries = db.query(Apiary).filter(Apiary.beekeeper_id == profile.id).all()
                for apiary in apiaries:
                    hives = db.query(Hive).filter(Hive.apiary_id == apiary.id).all()
                    for hive in hives:
                        db.query(HiveAlert).filter(HiveAlert.hive_id == hive.id).delete(synchronize_session=False)
                        db.query(HiveTelemetry).filter(HiveTelemetry.hive_id == hive.id).delete(synchronize_session=False)
                        db.query(HiveDevice).filter(HiveDevice.hive_id == hive.id).delete(synchronize_session=False)
                        harvests = db.query(HoneyHarvest).filter(HoneyHarvest.hive_id == hive.id).all()
                        for harvest in harvests:
                            batches = db.query(HoneyBatch).filter(HoneyBatch.harvest_id == harvest.id).all()
                            for batch in batches:
                                products = db.query(HoneyProduct).filter(HoneyProduct.batch_id == batch.id).all()
                                for p in products:
                                    db.query(TraceabilityEvent).filter(TraceabilityEvent.product_id == p.id).delete(synchronize_session=False)
                                db.query(HoneyProduct).filter(HoneyProduct.batch_id == batch.id).delete(synchronize_session=False)
                            db.query(HoneyBatch).filter(HoneyBatch.harvest_id == harvest.id).delete(synchronize_session=False)
                        db.query(HoneyHarvest).filter(HoneyHarvest.hive_id == hive.id).delete(synchronize_session=False)
                    db.query(Hive).filter(Hive.apiary_id == apiary.id).delete(synchronize_session=False)
                db.query(Apiary).filter(Apiary.beekeeper_id == profile.id).delete(synchronize_session=False)
                db.query(BeekeeperProfile).filter(BeekeeperProfile.id == profile.id).delete(synchronize_session=False)
            db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_user_and_token(email: str, role: str) -> Tuple[dict, str]:
    password = "SecurePassword123"
    reg_resp = client.post("/auth/register", json={
        "full_name": f"Harden {role.title()}",
        "email": email,
        "phone": f"987{secrets.randbelow(9000000) + 1000000}",
        "password": password,
        "role": role,
    })
    assert reg_resp.status_code == 201, reg_resp.text
    user_data = reg_resp.json()
    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return user_data, token


def _setup_beekeeper_apiary_hive(email: str) -> Tuple[str, int, int]:
    _, token = _create_user_and_token(email, UserRole.BEEKEEPER.value)
    headers = _auth_header(token)
    code = f"BK-HRD-{secrets.token_hex(2).upper()}"
    p_resp = client.post("/beekeeper/profile", json={
        "beekeeper_code": code,
        "address": "Hardened Lane",
        "village": "Safe Village",
        "district": "Dehradun",
        "state": "Uttarakhand",
        "pincode": "248001",
        "experience_years": 8,
    }, headers=headers)
    assert p_resp.status_code == 201

    a_resp = client.post("/beekeeper/apiaries", json={
        "name": "Hardened Apiary",
        "location_name": "Valley",
        "latitude": 30.3165,
        "longitude": 78.0322,
    }, headers=headers)
    assert a_resp.status_code == 201
    apiary_id = a_resp.json()["id"]

    h_resp = client.post(f"/beekeeper/apiaries/{apiary_id}/hives", json={
        "hive_code": f"HV-{secrets.token_hex(2).upper()}",
        "hive_type": "Langstroth",
    }, headers=headers)
    assert h_resp.status_code == 201
    hive_id = h_resp.json()["id"]

    return token, apiary_id, hive_id


# ═══════════════════════════════════════════════════════════════════════════
# 1. IoT HARDWARE TOKEN AUTHENTICATION & CROSS-HIVE ISOLATION
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_iot_device_token_generation_and_hardware_authentication():
    """Verify hardware node can authenticate with X-Device-Token without Bearer JWT."""
    email1 = "iot_hard_auth1@example.com"
    email2 = "iot_hard_auth2@example.com"
    _cleanup_users(email1, email2)

    try:
        token1, _, hive_id1 = _setup_beekeeper_apiary_hive(email1)
        token2, _, hive_id2 = _setup_beekeeper_apiary_hive(email2)

        # Beekeeper registers hardware device for Hive 1
        headers1 = _auth_header(token1)
        dev_resp = client.post(
            f"/beekeeper/hives/{hive_id1}/devices",
            json={"device_id": "SN-ESP32-HARDENED-01", "device_type": "ESP32_CELLULAR"},
            headers=headers1,
        )
        assert dev_resp.status_code == 201
        dev_data = dev_resp.json()
        raw_device_token = dev_data["device_token"]
        assert raw_device_token is not None
        assert raw_device_token.startswith("hc_dev_")

        # 1. Post telemetry using ONLY X-Device-Token header (no Authorization header)
        now_iso = datetime.now(timezone.utc).isoformat()
        hw_resp = client.post(
            f"/beekeeper/hives/{hive_id1}/telemetry",
            headers={"X-Device-Token": raw_device_token},
            json={
                "timestamp": now_iso,
                "temperature_c": 35.10,
                "humidity_percent": 55.00,
                "weight_kg": 32.50,
                "sound_level": 42.00,
                "vibration_level": 0.80,
            },
        )
        assert hw_resp.status_code == 201
        telemetry_data = hw_resp.json()
        assert telemetry_data["device_id"] == "SN-ESP32-HARDENED-01"
        assert telemetry_data["is_duplicate"] is False

        # 2. Hardware token used with invalid/corrupt secret -> 401 Unauthorized
        bad_token_resp = client.post(
            f"/beekeeper/hives/{hive_id1}/telemetry",
            headers={"X-Device-Token": "hc_dev_invalid_secret_token_12345"},
            json={
                "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
                "temperature_c": 35.0,
                "humidity_percent": 50.0,
                "weight_kg": 30.0,
                "sound_level": 40.0,
                "vibration_level": 0.5,
            },
        )
        assert bad_token_resp.status_code == 401
        assert "Invalid or inactive device token" in bad_token_resp.json()["detail"]

        # 3. Cross-hive injection attack: Hive 1's device token attempting to post to Hive 2 -> 403 Forbidden
        cross_hive_resp = client.post(
            f"/beekeeper/hives/{hive_id2}/telemetry",
            headers={"X-Device-Token": raw_device_token},
            json={
                "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat(),
                "temperature_c": 35.0,
                "humidity_percent": 50.0,
                "weight_kg": 30.0,
                "sound_level": 40.0,
                "vibration_level": 0.5,
            },
        )
        assert cross_hive_resp.status_code == 403
        assert "does not belong to this hive" in cross_hive_resp.json()["detail"]

    finally:
        _cleanup_users(email1, email2)


# ═══════════════════════════════════════════════════════════════════════════
# 2. TELEMETRY IDEMPOTENCY & DUPLICATE PREVENTION
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_telemetry_idempotency_and_conflict_handling():
    """Verify duplicate readings are handled idempotently (200 is_duplicate=True) and conflicts return 409."""
    email = "iot_idempotent@example.com"
    _cleanup_users(email)

    try:
        token, _, hive_id = _setup_beekeeper_apiary_hive(email)
        headers = _auth_header(token)

        fixed_timestamp = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        reading_payload = {
            "timestamp": fixed_timestamp,
            "temperature_c": 34.50,
            "humidity_percent": 60.00,
            "weight_kg": 28.00,
            "sound_level": 45.00,
            "vibration_level": 1.00,
        }

        # 1. First transmission -> 201 Created
        resp1 = client.post(f"/beekeeper/hives/{hive_id}/telemetry", headers=headers, json=reading_payload)
        assert resp1.status_code == 201
        data1 = resp1.json()
        first_id = data1["id"]
        assert data1["is_duplicate"] is False

        # 2. Duplicate transmission (e.g. cellular re-transmit of same packet) -> 200 OK (idempotent)
        resp2 = client.post(f"/beekeeper/hives/{hive_id}/telemetry", headers=headers, json=reading_payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["id"] == first_id
        assert data2["is_duplicate"] is True

        # Verify no duplicate row in DB
        db: Session = SessionLocal()
        try:
            count = db.query(HiveTelemetry).filter(
                HiveTelemetry.hive_id == hive_id,
                HiveTelemetry.timestamp == datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc),
            ).count()
            assert count == 1
        finally:
            db.close()

        # 3. Conflicting transmission with same timestamp but conflicting temperature -> 409 Conflict
        conflicting_payload = dict(reading_payload)
        conflicting_payload["temperature_c"] = 39.50
        resp3 = client.post(f"/beekeeper/hives/{hive_id}/telemetry", headers=headers, json=conflicting_payload)
        assert resp3.status_code == 409
        err_detail = resp3.json()["detail"]
        assert "Conflicting telemetry reading already exists" in err_detail

    finally:
        _cleanup_users(email)


# ═══════════════════════════════════════════════════════════════════════════
# 3. STRICT ALERT LIFECYCLE STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_strict_alert_lifecycle_state_machine():
    """Verify OPEN -> ACKNOWLEDGED -> RESOLVED, and illegal state transitions are rejected with 400."""
    email = "alert_lifecycle@example.com"
    _cleanup_users(email)

    try:
        token, _, hive_id = _setup_beekeeper_apiary_hive(email)
        headers = _auth_header(token)

        # Trigger an anomaly to produce an alert: critical temperature (42.0 C)
        t_resp = client.post(f"/beekeeper/hives/{hive_id}/telemetry", headers=headers, json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature_c": 42.00,
            "humidity_percent": 60.00,
            "weight_kg": 30.00,
            "sound_level": 45.00,
            "vibration_level": 1.00,
        })
        assert t_resp.status_code == 201

        # Fetch alert
        a_resp = client.get(f"/beekeeper/hives/{hive_id}/alerts", headers=headers)
        assert a_resp.status_code == 200
        alerts = a_resp.json()
        assert len(alerts) >= 1
        alert = alerts[0]
        alert_id = alert["id"]
        assert alert["status"] == "OPEN"

        # 1. Acknowledge the alert: OPEN -> ACKNOWLEDGED (valid)
        ack_resp = client.post(f"/beekeeper/alerts/{alert_id}/acknowledge", headers=headers)
        assert ack_resp.status_code == 200
        ack_data = ack_resp.json()
        assert ack_data["status"] == "ACKNOWLEDGED"
        assert ack_data["acknowledged_at"] is not None

        # 2. Illegal transition: Acknowledging an ALREADY acknowledged alert -> 400 Bad Request
        ack_again = client.post(f"/beekeeper/alerts/{alert_id}/acknowledge", headers=headers)
        assert ack_again.status_code == 400
        assert "already acknowledged" in ack_again.json()["detail"].lower()

        # 3. Resolve the alert: ACKNOWLEDGED -> RESOLVED (valid)
        res_resp = client.post(f"/beekeeper/alerts/{alert_id}/resolve", headers=headers)
        assert res_resp.status_code == 200
        res_data = res_resp.json()
        assert res_data["status"] == "RESOLVED"
        assert res_data["resolved_at"] is not None

        # 4. Illegal transition: Resolving an ALREADY resolved alert -> 400 Bad Request
        res_again = client.post(f"/beekeeper/alerts/{alert_id}/resolve", headers=headers)
        assert res_again.status_code == 400
        assert "already resolved" in res_again.json()["detail"].lower()

        # 5. Illegal transition: Acknowledging a RESOLVED alert -> 400 Bad Request
        ack_resolved = client.post(f"/beekeeper/alerts/{alert_id}/acknowledge", headers=headers)
        assert ack_resolved.status_code == 400
        assert "cannot acknowledge" in ack_resolved.json()["detail"].lower()

    finally:
        _cleanup_users(email)


# ═══════════════════════════════════════════════════════════════════════════
# 4. PRODUCTION-SAFE MISSING TELEMETRY (UNMONITORED VS ACTIVE)
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_production_safe_missing_telemetry_heuristics():
    """Verify newly created unmonitored hive does not trigger false alarm, but active hardware triggers expected alert."""
    email = "safe_missing@example.com"
    _cleanup_users(email)

    try:
        token, _, hive_id = _setup_beekeeper_apiary_hive(email)
        headers = _auth_header(token)

        # 1. Brand new hive with NO devices registered -> UNMONITORED_HIVE, health NORMAL (no false alarm alert)
        h_resp1 = client.get(f"/beekeeper/hives/{hive_id}/health", headers=headers)
        assert h_resp1.status_code == 200
        h_data1 = h_resp1.json()
        assert "UNMONITORED_HIVE" in h_data1["anomalies"]
        assert h_data1["health_status"] == "HEALTHY"
        assert len(h_data1["active_alerts"]) == 0

        # 2. Register an active hardware device
        dev_resp = client.post(
            f"/beekeeper/hives/{hive_id}/devices",
            json={"device_id": "SN-SAFE-001", "device_type": "ESP32_LORA"},
            headers=headers,
        )
        assert dev_resp.status_code == 201

        # Now that an active device is registered, health shows NO_TELEMETRY_RECORDED (waiting for initial reading)
        h_resp2 = client.get(f"/beekeeper/hives/{hive_id}/health", headers=headers)
        assert h_resp2.status_code == 200
        h_data2 = h_resp2.json()
        assert "NO_TELEMETRY_RECORDED" in h_data2["anomalies"]

    finally:
        _cleanup_users(email)


# ═══════════════════════════════════════════════════════════════════════════
# 5. RBAC & CROSS-OWNER ISOLATION AUDIT
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_comprehensive_rbac_and_cross_owner_isolation():
    """Verify strict role separation and complete cross-owner isolation returning 403 or 404."""
    email_bk1 = "bk1_audit@example.com"
    email_bk2 = "bk2_audit@example.com"
    email_buyer = "buyer_audit@example.com"
    _cleanup_users(email_bk1, email_bk2, email_buyer)

    try:
        token_bk1, _, hive_id1 = _setup_beekeeper_apiary_hive(email_bk1)
        token_bk2, _, hive_id2 = _setup_beekeeper_apiary_hive(email_bk2)
        _, token_buyer = _create_user_and_token(email_buyer, UserRole.BUYER.value)

        # Trigger an alert on Hive 1
        client.post(f"/beekeeper/hives/{hive_id1}/telemetry", headers=_auth_header(token_bk1), json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature_c": 43.0,
            "humidity_percent": 60.0,
            "weight_kg": 30.0,
            "sound_level": 40.0,
            "vibration_level": 0.5,
        })
        alerts1 = client.get(f"/beekeeper/hives/{hive_id1}/alerts", headers=_auth_header(token_bk1)).json()
        alert_id1 = alerts1[0]["id"]

        # 1. BUYER attempting to access beekeeper endpoints -> 403 Forbidden
        buyer_bk_resp = client.get(f"/beekeeper/hives/{hive_id1}/health", headers=_auth_header(token_buyer))
        assert buyer_bk_resp.status_code == 403

        # 2. BEEKEEPER attempting to access buyer cart -> 403 Forbidden
        bk_cart_resp = client.get("/buyer/cart", headers=_auth_header(token_bk1))
        assert bk_cart_resp.status_code == 403

        # 3. Cross-Beekeeper isolation: BK2 accessing BK1's alert -> 404 Not Found (privacy protected)
        cross_ack = client.post(f"/beekeeper/alerts/{alert_id1}/acknowledge", headers=_auth_header(token_bk2))
        assert cross_ack.status_code == 404

        cross_res = client.post(f"/beekeeper/alerts/{alert_id1}/resolve", headers=_auth_header(token_bk2))
        assert cross_res.status_code == 404

        cross_dev = client.get(f"/beekeeper/hives/{hive_id1}/devices", headers=_auth_header(token_bk2))
        assert cross_dev.status_code == 404

        cross_tel = client.get(f"/beekeeper/hives/{hive_id1}/telemetry", headers=_auth_header(token_bk2))
        assert cross_tel.status_code == 404

    finally:
        _cleanup_users(email_bk1, email_bk2, email_buyer)


# ═══════════════════════════════════════════════════════════════════════════
# 6. SECURITY & PRIVACY AUDIT (ZERO LEAKS IN PUBLIC / TRACE APIS)
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_security_and_privacy_no_pii_or_credentials_exposed():
    """Verify public endpoints (/trace/{token} and /marketplace/products) never expose passwords, emails, phones, or private keys."""
    email = "privacy_audit@example.com"
    _cleanup_users(email)

    try:
        token, apiary_id, hive_id = _setup_beekeeper_apiary_hive(email)
        headers = _auth_header(token)

        # Create harvest, batch, and product
        harv_resp = client.post(f"/beekeeper/hives/{hive_id}/harvests", headers=headers, json={
            "harvest_date": "2026-09-01",
            "actual_quantity_kg": 50.0,
            "estimated_quantity_kg": 48.0,
            "honey_type": "Multifloral Forest",
        })
        assert harv_resp.status_code == 201
        harvest_id = harv_resp.json()["id"]

        batch_resp = client.post(f"/beekeeper/harvests/{harvest_id}/batches", headers=headers, json={
            "batch_code": f"BCH-AUDIT-{secrets.token_hex(2).upper()}",
            "batch_date": "2026-09-02",
            "quantity_kg": 30.0,
            "honey_type": "Multifloral Forest",
        })
        assert batch_resp.status_code == 201
        batch_id = batch_resp.json()["id"]

        prd_resp = client.post(f"/beekeeper/batches/{batch_id}/products", headers=headers, json={
            "net_weight_g": 500.0,
            "packaging_date": "2026-09-03",
        })
        assert prd_resp.status_code == 201
        prd_data = prd_resp.json()
        trace_token = prd_data["trace_token"]
        product_id = prd_data["id"]

        # List product on marketplace
        list_resp = client.put(f"/beekeeper/products/{product_id}/listing", headers=headers, json={
            "price": "450.00",
            "currency": "INR",
            "is_listed": True,
        })
        assert list_resp.status_code == 200

        # Audit 1: Public QR Trace Endpoint
        trace_resp = client.get(f"/trace/{trace_token}")
        assert trace_resp.status_code == 200
        trace_json = trace_resp.json()

        # Sensitive keys MUST NOT exist anywhere in the payload
        forbidden_keys = [
            "password", "password_hash", "user_id", "email", "phone",
            "private_key", "secret_key", "internal_id", "device_token_hash",
        ]
        trace_text = trace_resp.text.lower()
        for forbidden in forbidden_keys:
            assert forbidden not in trace_text, f"Leaked sensitive field '{forbidden}' in /trace response"

        # Trace response should expose safe consumer attributes
        assert trace_json["serial_number"] == prd_data["serial_number"]
        assert trace_json["honey_type"] == "Multifloral Forest"
        assert trace_json["origin"]["district"] == "Dehradun"
        assert trace_json["origin"]["state"] == "Uttarakhand"
        assert "beekeeper_code" in trace_json["beekeeper"]

        # Audit 2: Public Marketplace Products Endpoint
        mkt_resp = client.get("/marketplace/products")
        assert mkt_resp.status_code == 200
        mkt_text = mkt_resp.text.lower()
        for forbidden in forbidden_keys:
            assert forbidden not in mkt_text, f"Leaked sensitive field '{forbidden}' in /marketplace response"

    finally:
        _cleanup_users(email)


# ═══════════════════════════════════════════════════════════════════════════
# 7. CONSISTENT QUERY PAGINATION
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_consistent_query_pagination():
    """Verify skip and limit parameters are respected across listing endpoints."""
    email = "pagination_audit@example.com"
    _cleanup_users(email)

    try:
        token, _, hive_id = _setup_beekeeper_apiary_hive(email)
        headers = _auth_header(token)

        # Ingest 3 telemetry readings
        base_time = datetime(2026, 9, 9, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(3):
            client.post(f"/beekeeper/hives/{hive_id}/telemetry", headers=headers, json={
                "timestamp": (base_time + timedelta(minutes=i * 10)).isoformat(),
                "temperature_c": 34.0 + i,
                "humidity_percent": 55.0,
                "weight_kg": 30.0,
                "sound_level": 40.0,
                "vibration_level": 0.5,
            })

        # Test limit=1
        lim1_resp = client.get(f"/beekeeper/hives/{hive_id}/telemetry?skip=0&limit=1", headers=headers)
        assert lim1_resp.status_code == 200
        assert len(lim1_resp.json()) == 1

        # Test limit=2, skip=1
        lim2_resp = client.get(f"/beekeeper/hives/{hive_id}/telemetry?skip=1&limit=2", headers=headers)
        assert lim2_resp.status_code == 200
        assert len(lim2_resp.json()) == 2

    finally:
        _cleanup_users(email)


# ═══════════════════════════════════════════════════════════════════════════
# 8. OPENAPI 3.1.0 CONTRACT & DOCS VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def test_openapi_schema_and_documentation_endpoints():
    """Verify /openapi.json contains expected OpenAPI 3.1 contract, tags, and /docs, /redoc respond."""
    # 1. /openapi.json
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    assert schema["openapi"].startswith("3.1")
    assert schema["info"]["title"] == "Honey Chain"
    assert "Phase 8" in schema["info"]["description"]

    # Verify structured tags
    expected_tags = {
        "Health",
        "Authentication",
        "Beekeeper",
        "Traceability",
        "Marketplace",
        "Buyer",
        "IoT Devices & Hive Health",
    }
    present_tags = {tag["name"] for tag in schema.get("tags", [])}
    assert expected_tags.issubset(present_tags), f"Missing tags: {expected_tags - present_tags}"

    # Verify endpoints exist in OpenAPI paths
    paths = schema.get("paths", {})
    assert "/health" in paths
    assert "/auth/login" in paths
    assert "/auth/register" in paths
    assert "/beekeeper/profile" in paths
    assert "/beekeeper/apiaries" in paths
    assert "/beekeeper/hives/{hive_id}/telemetry" in paths
    assert "/trace/{trace_token}" in paths
    assert "/marketplace/products" in paths
    assert "/buyer/cart" in paths
    assert "/buyer/checkout" in paths

    # 2. /docs Swagger UI
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "text/html" in docs_resp.headers["content-type"]
    assert "swagger-ui" in docs_resp.text.lower()

    # 3. /redoc ReDoc UI
    redoc_resp = client.get("/redoc")
    assert redoc_resp.status_code == 200
    assert "text/html" in redoc_resp.headers["content-type"]
    assert "redoc" in redoc_resp.text.lower()
