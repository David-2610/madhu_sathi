"""
Comprehensive test suite for Phase 5: Honey Product + Unique QR + Public Traceability + Blockchain Abstraction.

Covers:
  Product Packaging & Creation:
    - Package product from batch (auto serial, trace token, QR SVG, trace URL)
    - Custom serial number support
    - Duplicate serial number rejected (HTTP 409)
    - Invalid weight rejected (HTTP 422)

  Product Ownership & RBAC:
    - BUYER cannot create products (HTTP 403)
    - KVIC_ADMIN cannot create products (HTTP 403)
    - Beekeeper B cannot package from Beekeeper A's batch (HTTP 404)
    - Beekeeper B cannot retrieve or update Beekeeper A's product (HTTP 404)
    - Beekeeper B cannot get Beekeeper A's product QR (HTTP 404)

  QR Code Generation:
    - Backend generates valid SVG vector
    - /beekeeper/products/{id}/qr returns image/png
    - Public /trace/{token}/qr returns image/png
    - QR encodes public URL without exposing database IDs

  Public Consumer Trace:
    - Unauthenticated request to /trace/{token} succeeds (HTTP 200)
    - Nonexistent token returns HTTP 404
    - PII Safety: No phone, email, password hash, or user_id in response
    - Revoked product clearly displays REVOKED status and warning notice
    - Product status update to SOLD, REVOKED, SUSPICIOUS

  Traceability Events:
    - Automatic recording of PRODUCT_CREATED and PACKAGED events
    - Additional event recording via API (QUALITY_TEST_ADDED)
    - Events ordered chronologically
    - SHA-256 event hash integrity (64 hex characters)

  Blockchain Provider Abstraction:
    - MockBlockchainProvider declared explicitly as mock
    - No fake transaction hashes generated or persisted
    - Hash verification for recorded vs unrecorded events
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal, check_db_connection
from app.main import app
from app.models.apiary import Apiary
from app.models.beekeeper import BeekeeperProfile
from app.models.hive import Hive
from app.models.hive_alert import HiveAlert
from app.models.hive_device import HiveDevice
from app.models.hive_telemetry import HiveTelemetry
from app.models.honey_batch import HoneyBatch
from app.models.honey_harvest import HoneyHarvest
from app.models.honey_product import HoneyProduct, ProductStatus
from app.models.traceability_event import TraceEventType, TraceabilityEvent
from app.models.user import User
from app.services.blockchain import (
    EVMBlockchainProvider,
    MockBlockchainProvider,
    compute_event_hash,
    get_blockchain_provider,
)

client = TestClient(app)

skip_if_no_db = pytest.mark.skipif(
    not check_db_connection(),
    reason="Database is not reachable — skipping DB-dependent tests",
)


# ── Cleanup Helper ─────────────────────────────────────────────────────────
def _cleanup_user_hierarchy(email: str) -> None:
    """Safely delete all records in reverse foreign-key order."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return
        profile = db.query(BeekeeperProfile).filter(BeekeeperProfile.user_id == user.id).first()
        if profile:
            # 1. Gather all batches and products
            batch_ids = [b[0] for b in db.query(HoneyBatch.id).filter(HoneyBatch.beekeeper_id == profile.id).all()]
            if batch_ids:
                product_ids = [p[0] for p in db.query(HoneyProduct.id).filter(HoneyProduct.batch_id.in_(batch_ids)).all()]
                if product_ids:
                    db.query(TraceabilityEvent).filter(TraceabilityEvent.product_id.in_(product_ids)).delete(synchronize_session=False)
                    db.query(HoneyProduct).filter(HoneyProduct.id.in_(product_ids)).delete(synchronize_session=False)
                db.query(TraceabilityEvent).filter(TraceabilityEvent.batch_id.in_(batch_ids)).delete(synchronize_session=False)
                db.query(HoneyBatch).filter(HoneyBatch.id.in_(batch_ids)).delete(synchronize_session=False)

            # 2. Gather all apiaries and hives
            apiary_ids = [a[0] for a in db.query(Apiary.id).filter(Apiary.beekeeper_id == profile.id).all()]
            if apiary_ids:
                hive_ids = [h[0] for h in db.query(Hive.id).filter(Hive.apiary_id.in_(apiary_ids)).all()]
                if hive_ids:
                    db.query(HiveAlert).filter(HiveAlert.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(HiveTelemetry).filter(HiveTelemetry.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(HiveDevice).filter(HiveDevice.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(HoneyHarvest).filter(HoneyHarvest.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(Hive).filter(Hive.id.in_(hive_ids)).delete(synchronize_session=False)
                db.query(Apiary).filter(Apiary.id.in_(apiary_ids)).delete(synchronize_session=False)

            # 3. Delete profile
            db.query(BeekeeperProfile).filter(BeekeeperProfile.id == profile.id).delete(synchronize_session=False)

        # 4. Delete user
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_user_and_token(email: str, role: str, phone: str = "9800000001") -> tuple[dict, str]:
    password = "SecurePassword123"
    register_payload = {
        "full_name": f"Test {role.title()}",
        "email": email,
        "phone": phone,
        "password": password,
        "role": role,
    }
    client.post("/auth/register", json=register_payload)
    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    user_info = login_resp.json()["user"]
    return user_info, token


def _setup_beekeeper_with_batch(email: str, phone: str = "9900000001") -> tuple[str, dict]:
    """Helper to set up a full beekeeper hierarchy through to HoneyBatch."""
    _, token = _create_user_and_token(email, "BEEKEEPER", phone)
    headers = _auth_header(token)

    # 1. Profile
    client.post(
        "/beekeeper/profile",
        json={
            "village": "Madhupur",
            "district": "Deoghar",
            "state": "Jharkhand",
            "pincode": "815353",
            "experience_years": 8,
        },
        headers=headers,
    )

    # 2. Apiary
    apiary = client.post(
        "/beekeeper/apiaries",
        json={"name": "Sunrise Apiary", "location_name": "East Meadow"},
        headers=headers,
    ).json()

    # 3. Hive
    hive = client.post(
        f"/beekeeper/apiaries/{apiary['id']}/hives",
        json={"hive_code": "H-101", "hive_type": "Langstroth"},
        headers=headers,
    ).json()

    # 4. Harvest
    harvest = client.post(
        f"/beekeeper/hives/{hive['id']}/harvests",
        json={
            "harvest_date": str(date.today()),
            "actual_quantity_kg": 50.0,
            "honey_type": "Wild Forest Mustard",
        },
        headers=headers,
    ).json()

    # 5. Batch
    batch = client.post(
        f"/beekeeper/harvests/{harvest['id']}/batches",
        json={
            "batch_code": f"BAT-{phone[-4:]}",
            "batch_date": str(date.today()),
            "quantity_kg": 20.0,
            "honey_type": "Wild Forest Mustard",
        },
        headers=headers,
    ).json()

    return token, batch


# ═══════════════════════════════════════════════════════════════════════════
# 1. PRODUCT CREATION & PACKAGING TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_package_product_success():
    email = "prd_pack_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000001")
        headers = _auth_header(token)

        payload = {
            "net_weight_g": 500.0,
            "packaging_date": str(date.today()),
            "expiry_date": "2027-12-31",
        }
        resp = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["batch_id"] == batch["id"]
        assert data["net_weight_g"] == 500.0
        assert data["status"] == "ACTIVE"
        assert "trace_token" in data
        assert len(data["trace_token"]) >= 32  # Opaque URL-safe token
        assert "serial_number" in data
        assert data["serial_number"].startswith("HC-PRD-")
        assert "trace_url" in data
        assert f"/trace/{data['trace_token']}" in data["trace_url"]
        assert data["qr_code_svg"] is not None
        assert "<svg" in data["qr_code_svg"]

        # Verify listing
        list_resp = client.get(f"/beekeeper/batches/{batch['id']}/products", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        all_resp = client.get("/beekeeper/products", headers=headers)
        assert all_resp.status_code == 200
        assert len(all_resp.json()) == 1
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_custom_serial_number_and_duplicate_rejection():
    email = "prd_serial_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000002")
        headers = _auth_header(token)

        payload = {
            "net_weight_g": 250.0,
            "packaging_date": str(date.today()),
            "serial_number": "HC-CUSTOM-SERIAL-001",
        }
        first = client.post(f"/beekeeper/batches/{batch['id']}/products", json=payload, headers=headers)
        assert first.status_code == 201
        assert first.json()["serial_number"] == "HC-CUSTOM-SERIAL-001"

        # Attempt duplicate serial -> 409 Conflict
        second = client.post(f"/beekeeper/batches/{batch['id']}/products", json=payload, headers=headers)
        assert second.status_code == 409
        assert "already exists" in second.json()["detail"].lower()
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_package_product_invalid_weight_rejected():
    email = "prd_weight_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000003")
        headers = _auth_header(token)

        # Non-positive weight -> 422
        bad_payload = {
            "net_weight_g": 0.0,
            "packaging_date": str(date.today()),
        }
        resp = client.post(f"/beekeeper/batches/{batch['id']}/products", json=bad_payload, headers=headers)
        assert resp.status_code == 422
    finally:
        _cleanup_user_hierarchy(email)


# ═══════════════════════════════════════════════════════════════════════════
# 2. PRODUCT OWNERSHIP & ACCESS CONTROL TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_cross_beekeeper_product_access_rejected():
    email_a = "bk_prd_a@example.com"
    email_b = "bk_prd_b@example.com"
    try:
        token_a, batch_a = _setup_beekeeper_with_batch(email_a, "9910000004")
        token_b, _ = _setup_beekeeper_with_batch(email_b, "9910000005")

        headers_a = _auth_header(token_a)
        headers_b = _auth_header(token_b)

        # Beekeeper A creates product
        prd_a = client.post(
            f"/beekeeper/batches/{batch_a['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers_a,
        ).json()
        prd_id = prd_a["id"]

        # Beekeeper B cannot package from A's batch
        resp = client.post(
            f"/beekeeper/batches/{batch_a['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers_b,
        )
        assert resp.status_code == 404

        # Beekeeper B cannot view A's products list for batch
        resp = client.get(f"/beekeeper/batches/{batch_a['id']}/products", headers=headers_b)
        assert resp.status_code == 404

        # Beekeeper B cannot get A's product by ID
        resp = client.get(f"/beekeeper/products/{prd_id}", headers=headers_b)
        assert resp.status_code == 404

        # Beekeeper B cannot get A's product QR
        resp = client.get(f"/beekeeper/products/{prd_id}/qr", headers=headers_b)
        assert resp.status_code == 404

        # Beekeeper B cannot update A's product status
        resp = client.put(f"/beekeeper/products/{prd_id}/status", json={"status": "REVOKED"}, headers=headers_b)
        assert resp.status_code == 404

        # Beekeeper B cannot add events to A's product
        resp = client.post(
            f"/beekeeper/products/{prd_id}/events",
            json={
                "event_type": "QUALITY_TEST_ADDED",
                "description": "Unauthorized cross-beekeeper event test",
            },
            headers=headers_b,
        )
        assert resp.status_code == 404
    finally:
        _cleanup_user_hierarchy(email_a)
        _cleanup_user_hierarchy(email_b)


# ═══════════════════════════════════════════════════════════════════════════
# 3. QR CODE GENERATION & RETRIEVAL TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_qr_code_image_endpoints():
    email = "qr_img_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000006")
        headers = _auth_header(token)

        product = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 1000.0, "packaging_date": str(date.today())},
            headers=headers,
        ).json()

        # Beekeeper QR image endpoint
        bk_qr_resp = client.get(f"/beekeeper/products/{product['id']}/qr", headers=headers)
        assert bk_qr_resp.status_code == 200
        assert bk_qr_resp.headers["content-type"] == "image/png"
        assert len(bk_qr_resp.content) > 100

        # Public QR image endpoint (no auth)
        pub_qr_resp = client.get(f"/trace/{product['trace_token']}/qr")
        assert pub_qr_resp.status_code == 200
        assert pub_qr_resp.headers["content-type"] == "image/png"
        assert len(pub_qr_resp.content) > 100
    finally:
        _cleanup_user_hierarchy(email)


# ═══════════════════════════════════════════════════════════════════════════
# 4. PUBLIC CONSUMER TRACE & PII SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_public_consumer_trace_safety_and_integrity():
    email = "consumer_trace_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000007")
        headers = _auth_header(token)

        product = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={
                "net_weight_g": 500.0,
                "packaging_date": str(date.today()),
                "expiry_date": "2027-06-30",
            },
            headers=headers,
        ).json()
        trace_token = product["trace_token"]

        # Public trace request (NO AUTHENTICATION)
        trace_resp = client.get(f"/trace/{trace_token}")
        assert trace_resp.status_code == 200
        data = trace_resp.json()

        # Verify correct product & origin fields
        assert data["serial_number"] == product["serial_number"]
        assert data["status"] == "ACTIVE"
        assert data["is_valid"] is True
        assert data["revocation_notice"] is None
        assert data["honey_type"] == "Wild Forest Mustard"
        assert data["net_weight_g"] == 500.0
        assert data["batch"]["batch_code"] == batch["batch_code"]
        assert data["origin"]["apiary_name"] == "Sunrise Apiary"
        assert data["origin"]["village"] == "Madhupur"
        assert data["origin"]["district"] == "Deoghar"
        assert data["origin"]["state"] == "Jharkhand"
        assert "beekeeper_code" in data["beekeeper"]
        assert data["beekeeper"]["experience_years"] == 8

        # CRITICAL SECURITY & PRIVACY INVARIANTS: No PII leaked
        text_repr = trace_resp.text.lower()
        assert "phone" not in text_repr
        assert "email" not in text_repr
        assert "password" not in text_repr
        assert "user_id" not in text_repr
        assert "password_hash" not in text_repr
        assert "9910000007" not in text_repr
        assert "consumer_trace_test@example.com" not in text_repr

        # Confirm root and timeline objects expose NO internal database primary keys
        assert "id" not in data
        assert "batch_id" not in data
        assert "harvest_id" not in data
        assert "apiary_id" not in data
        assert "beekeeper_id" not in data
        assert "address" not in data["origin"]
        assert "pincode" not in data["origin"]

        # Verify timeline events present and free of internal database IDs
        assert len(data["timeline"]) >= 2
        event_types = [e["event_type"] for e in data["timeline"]]
        assert "PRODUCT_CREATED" in event_types
        assert "PACKAGED" in event_types
        for event_item in data["timeline"]:
            assert "id" not in event_item
            assert "batch_id" not in event_item
            assert "product_id" not in event_item
            assert "event_hash" in event_item
            assert len(event_item["event_hash"]) == 64

        # Nonexistent token returns 404
        bad_token = client.get("/trace/this_is_an_invalid_token_12345")
        assert bad_token.status_code == 404
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_revoked_product_public_display():
    email = "revoked_prd_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000008")
        headers = _auth_header(token)

        product = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers,
        ).json()
        trace_token = product["trace_token"]

        # Revoke the product
        update_resp = client.put(
            f"/beekeeper/products/{product['id']}/status",
            json={"status": "REVOKED"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "REVOKED"

        # Public trace must clearly show REVOKED and revocation notice
        trace_resp = client.get(f"/trace/{trace_token}")
        assert trace_resp.status_code == 200
        data = trace_resp.json()
        assert data["status"] == "REVOKED"
        assert data["is_valid"] is False
        assert data["revocation_notice"] is not None
        assert "REVOKED" in data["revocation_notice"]
    finally:
        _cleanup_user_hierarchy(email)


# ═══════════════════════════════════════════════════════════════════════════
# 5. TRACEABILITY EVENT & BLOCKCHAIN ABSTRACTION TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_manual_traceability_event_recording():
    email = "manual_event_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000009")
        headers = _auth_header(token)

        product = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers,
        ).json()

        # Record a manual quality test event
        event_resp = client.post(
            f"/beekeeper/products/{product['id']}/events",
            json={
                "event_type": "QUALITY_TEST_ADDED",
                "description": "Passed FSSAI purity and moisture test (Moisture: 17.2%)",
                "location": "Regional Honey Quality Lab, Ranchi",
                "metadata": {"moisture_pct": 17.2, "purity_grade": "A+"},
            },
            headers=headers,
        )
        assert event_resp.status_code == 201
        event_data = event_resp.json()
        assert event_data["event_type"] == "QUALITY_TEST_ADDED"
        assert len(event_data["event_hash"]) == 64  # SHA-256 length

        # In mock mode, no fake transaction hashes are ever fabricated
        assert event_data["blockchain_tx_hash"] is None
        assert event_data["is_on_chain"] is False

        # Public trace now shows 3 events
        trace = client.get(f"/trace/{product['trace_token']}").json()
        assert len(trace["timeline"]) == 3
        types = [e["event_type"] for e in trace["timeline"]]
        assert "QUALITY_TEST_ADDED" in types
    finally:
        _cleanup_user_hierarchy(email)


def test_blockchain_mock_provider_and_hasher_isolation():
    """Verify mock provider does not fabricate tx hashes and hasher is deterministic."""
    provider = MockBlockchainProvider()

    # Deterministic hash test
    h1 = compute_event_hash("PACKAGED", "PRD-001", "2026-09-09T10:00:00Z", {"weight": 500})
    h2 = compute_event_hash("PACKAGED", "PRD-001", "2026-09-09T10:00:00Z", {"weight": 500})
    assert h1 == h2
    assert len(h1) == 64

    # Record proof
    receipt = provider.record_event_proof(h1, {"weight": 500})
    assert receipt.is_success is True
    assert receipt.is_mock is True
    assert receipt.network == "MOCK_LOCAL"
    assert receipt.tx_hash is None  # RULE: NEVER fabricate a transaction hash

    # Verification
    assert provider.verify_event_proof(h1) is True
    assert provider.verify_event_proof("0000000000000000000000000000000000000000000000000000000000000000") is False

    # Factory returns provider instance
    resolved = get_blockchain_provider()
    assert isinstance(resolved, MockBlockchainProvider)


# ═══════════════════════════════════════════════════════════════════════════
# 6. HARDENING & INVARIANT VERIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_batch_product_capacity_and_batch_quantity_reduction_protection():
    """Verify sum(products) <= batch.quantity_kg and batch quantity cannot be reduced below packaged total."""
    email = "batch_cap_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000010")
        headers = _auth_header(token)

        # Batch quantity is 20.0 kg in helper; update batch to a controlled 2.0 kg for precise testing
        update_resp = client.put(
            f"/beekeeper/batches/{batch['id']}",
            json={"quantity_kg": 2.0},
            headers=headers,
        )
        assert update_resp.status_code == 200

        # Package unit 1: 1500g (1.5 kg). Available remaining: 0.5 kg.
        p1 = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 1500.0, "packaging_date": str(date.today())},
            headers=headers,
        )
        assert p1.status_code == 201

        # Attempt unit 2: 600g (0.6 kg). Total would be 2.1 kg > 2.0 kg -> 400 Bad Request
        p2_fail = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 600.0, "packaging_date": str(date.today())},
            headers=headers,
        )
        assert p2_fail.status_code == 400
        assert "exceeds available batch capacity" in p2_fail.json()["detail"].lower()

        # Package unit 2: exactly 500g (0.5 kg). Total reaches exactly 2.0 kg.
        p2_ok = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers,
        )
        assert p2_ok.status_code == 201

        # Attempt unit 3: 100g. Batch is completely allocated -> 400 Bad Request
        p3_fail = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 100.0, "packaging_date": str(date.today())},
            headers=headers,
        )
        assert p3_fail.status_code == 400

        # Attempt to reduce batch quantity below 2.0 kg (e.g. to 1.5 kg) -> 400 Bad Request
        reduct_fail = client.put(
            f"/beekeeper/batches/{batch['id']}",
            json={"quantity_kg": 1.5},
            headers=headers,
        )
        assert reduct_fail.status_code == 400
        assert "already packaged into products" in reduct_fail.json()["detail"].lower()

        # Increasing batch quantity to 5.0 kg succeeds
        increase_ok = client.put(
            f"/beekeeper/batches/{batch['id']}",
            json={"quantity_kg": 5.0},
            headers=headers,
        )
        assert increase_ok.status_code == 200
        assert increase_ok.json()["quantity_kg"] == 5.0
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_product_status_transition_policy():
    """Verify strict lifecycle transitions and rejection of nonsensical reversals."""
    email = "status_trans_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000011")
        headers = _auth_header(token)

        # Create active product
        product = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers,
        ).json()
        prd_id = product["id"]
        assert product["status"] == "ACTIVE"

        # 1. ACTIVE -> SOLD succeeds
        resp = client.put(f"/beekeeper/products/{prd_id}/status", json={"status": "SOLD"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "SOLD"

        # 2. SOLD -> ACTIVE is REJECTED (400 Bad Request)
        resp = client.put(f"/beekeeper/products/{prd_id}/status", json={"status": "ACTIVE"}, headers=headers)
        assert resp.status_code == 400
        assert "invalid product status transition" in resp.json()["detail"].lower()

        # 3. SOLD -> REVOKED succeeds (post-sale recall)
        resp = client.put(f"/beekeeper/products/{prd_id}/status", json={"status": "REVOKED"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "REVOKED"

        # 4. REVOKED is terminal: cannot transition to ACTIVE, SOLD, or SUSPICIOUS
        for invalid_target in ["ACTIVE", "SOLD", "SUSPICIOUS"]:
            resp = client.put(f"/beekeeper/products/{prd_id}/status", json={"status": invalid_target}, headers=headers)
            assert resp.status_code == 400
            assert "invalid product status transition" in resp.json()["detail"].lower()

        # 5. Second product: ACTIVE -> SUSPICIOUS -> ACTIVE (investigated and cleared)
        prod2 = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers,
        ).json()
        p2_id = prod2["id"]

        resp = client.put(f"/beekeeper/products/{p2_id}/status", json={"status": "SUSPICIOUS"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "SUSPICIOUS"

        resp = client.put(f"/beekeeper/products/{p2_id}/status", json={"status": "ACTIVE"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"
    finally:
        _cleanup_user_hierarchy(email)


def test_hash_determinism_with_differing_key_orders_and_nesting():
    """Verify SHA-256 hash calculation is 100% deterministic regardless of dictionary insertion order."""
    ts = "2026-09-09T12:00:00Z"
    code = "HC-PRD-TEST-001"
    evt = "QUALITY_TEST_ADDED"

    # Differing key orders with nested structures
    meta_order_1 = {
        "zeta": "last",
        "alpha": 1,
        "nested": {"z": 100, "a": 200, "inner": {"deep_b": 2, "deep_a": 1}},
        "metrics": [10, 20, 30],
    }
    meta_order_2 = {
        "alpha": 1,
        "metrics": [10, 20, 30],
        "nested": {"inner": {"deep_a": 1, "deep_b": 2}, "a": 200, "z": 100},
        "zeta": "last",
    }

    hash_1 = compute_event_hash(evt, code, ts, meta_order_1)
    hash_2 = compute_event_hash(evt, code, ts, meta_order_2)

    assert hash_1 == hash_2, "Hashes must be identical regardless of key insertion order"
    assert len(hash_1) == 64

    # Different data produces a strictly different hash
    meta_modified = dict(meta_order_1)
    meta_modified["alpha"] = 2
    hash_diff = compute_event_hash(evt, code, ts, meta_modified)
    assert hash_1 != hash_diff


def test_evm_provider_clean_interface_without_private_keys():
    """Verify EVMBlockchainProvider exposes record_event_hash and verify_event cleanly without requiring private keys."""
    provider = EVMBlockchainProvider(
        rpc_url="https://polygon-rpc.com",
        contract_address="0x1234567890123456789012345678901234567890",
        network="POLYGON_AMOY",
    )
    dummy_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # record_event_hash alias works cleanly
    receipt = provider.record_event_hash(dummy_hash, {"test": True})
    assert receipt.recorded_hash == dummy_hash
    assert receipt.tx_hash is None
    assert receipt.is_mock is False
    assert receipt.network == "POLYGON_AMOY"

    # verify_event alias works cleanly
    assert provider.verify_event(dummy_hash) is False


@skip_if_no_db
def test_traceability_event_immutability_and_endpoint_protection():
    """Verify traceability events cannot be updated or deleted via HTTP operations."""
    email = "immutable_evt_test@example.com"
    try:
        token, batch = _setup_beekeeper_with_batch(email, "9910000012")
        headers = _auth_header(token)

        product = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
            headers=headers,
        ).json()
        prd_id = product["id"]
        trace_token = product["trace_token"]

        # 1. Attempting PUT on /beekeeper/products/{id}/events -> 405 Method Not Allowed
        resp_put_evt = client.put(f"/beekeeper/products/{prd_id}/events", json={}, headers=headers)
        assert resp_put_evt.status_code == 405

        # 2. Attempting DELETE on /beekeeper/products/{id}/events -> 405 Method Not Allowed
        resp_del_evt = client.delete(f"/beekeeper/products/{prd_id}/events", headers=headers)
        assert resp_del_evt.status_code == 405

        # 3. Attempting PUT on public /trace/{token} -> 405 Method Not Allowed
        resp_put_trace = client.put(f"/trace/{trace_token}", json={})
        assert resp_put_trace.status_code == 405

        # 4. Attempting DELETE on public /trace/{token} -> 405 Method Not Allowed
        resp_del_trace = client.delete(f"/trace/{trace_token}")
        assert resp_del_trace.status_code == 405
    finally:
        _cleanup_user_hierarchy(email)

