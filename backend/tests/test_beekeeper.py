"""
Comprehensive test suite for Phase 4: Beekeeper + Apiary + Hive + Honey Lifecycle.

Covers:
  Authentication & RBAC:
    - Unauthenticated requests rejected
    - BUYER cannot access beekeeper endpoints (HTTP 403)
    - KVIC_ADMIN cannot access beekeeper endpoints (HTTP 403)

  Beekeeper Profile:
    - Create profile (success)
    - Duplicate profile rejected (HTTP 409)
    - Duplicate beekeeper code rejected (HTTP 409)
    - Retrieve own profile
    - Retrieve profile before creation (HTTP 404)
    - Update own profile

  Apiary:
    - Create apiary
    - Apiary creation requires profile first (HTTP 400)
    - Latitude/Longitude range validation (HTTP 422)
    - List own apiaries
    - Retrieve own apiary
    - Update own apiary
    - Delete own apiary (HTTP 204)
    - Cross-beekeeper apiary access rejected (HTTP 404)
    - Cannot delete apiary with existing hives (HTTP 400)

  Hive:
    - Create hive
    - Duplicate hive code in same apiary rejected (HTTP 409)
    - List hives in apiary
    - Retrieve and update hive
    - Delete hive (HTTP 204)
    - Cross-beekeeper hive access rejected (HTTP 404)
    - Cannot delete hive with recorded harvests (HTTP 400)

  Harvest:
    - Create harvest
    - Reject negative actual/estimated quantities (HTTP 422)
    - List harvests by hive
    - Retrieve harvest
    - Cross-beekeeper harvest access rejected (HTTP 404)

  Honey Batch:
    - Create batch from harvest
    - Reject negative batch quantity (HTTP 422)
    - Reject quantity greater than available harvest quantity (HTTP 400)
    - Multiple batches respect total harvest capacity
    - Duplicate batch code rejected (HTTP 409)
    - List and retrieve batches
    - Update batch status and quantity
    - Cross-beekeeper batch access rejected (HTTP 404)

  Database Foreign Key Constraints:
    - ondelete="RESTRICT" blocks deletion of parent when child exists
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import SessionLocal, check_db_connection
from app.main import app
from app.models.apiary import Apiary
from app.models.beekeeper import BeekeeperProfile
from app.models.hive import Hive, HiveStatus
from app.models.hive_alert import HiveAlert
from app.models.hive_device import HiveDevice
from app.models.hive_telemetry import HiveTelemetry
from app.models.honey_batch import BatchStatus, HoneyBatch
from app.models.honey_harvest import HoneyHarvest
from app.models.honey_product import HoneyProduct
from app.models.traceability_event import TraceabilityEvent
from app.models.user import User

client = TestClient(app)

skip_if_no_db = pytest.mark.skipif(
    not check_db_connection(),
    reason="Database is not reachable — skipping DB-dependent tests",
)


# ── Cleanup Helper ─────────────────────────────────────────────────────────
def _cleanup_user_hierarchy(email: str) -> None:
    """Safely delete a user and all child beekeeping records in reverse order."""
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
    """Helper to register and login a user, returning (user_dict, access_token)."""
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


# ═══════════════════════════════════════════════════════════════════════════
# 1. AUTHENTICATION & RBAC TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_unauthenticated_requests_to_beekeeper_endpoints_rejected():
    """Unauthenticated requests to any /beekeeper endpoint must be rejected."""
    endpoints = [
        ("GET", "/beekeeper/profile"),
        ("POST", "/beekeeper/profile"),
        ("GET", "/beekeeper/apiaries"),
        ("POST", "/beekeeper/apiaries"),
        ("GET", "/beekeeper/batches"),
    ]
    for method, path in endpoints:
        resp = client.request(method, path)
        assert resp.status_code in (401, 403), f"{method} {path} returned {resp.status_code}"


@skip_if_no_db
def test_buyer_cannot_access_beekeeper_endpoints():
    """A BUYER must receive HTTP 403 when calling any /beekeeper endpoint."""
    email = "buyer_rbac_test@example.com"
    try:
        _, token = _create_user_and_token(email, "BUYER", "9811111111")
        headers = _auth_header(token)

        resp = client.get("/beekeeper/profile", headers=headers)
        assert resp.status_code == 403

        resp = client.post("/beekeeper/profile", json={"address": "Test"}, headers=headers)
        assert resp.status_code == 403

        resp = client.get("/beekeeper/apiaries", headers=headers)
        assert resp.status_code == 403

        resp = client.get("/beekeeper/batches", headers=headers)
        assert resp.status_code == 403
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_kvic_admin_cannot_access_beekeeper_endpoints():
    """A KVIC_ADMIN must receive HTTP 403 when calling beekeeper-only endpoints."""
    email = "kvic_rbac_test@example.com"
    db: Session = SessionLocal()
    try:
        # Provision KVIC admin directly in DB
        admin = User(
            full_name="KVIC Officer",
            email=email,
            phone="9822222222",
            password_hash=hash_password("SecurePassword123"),
            role="KVIC_ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        login_resp = client.post(
            "/auth/login", json={"email": email, "password": "SecurePassword123"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = _auth_header(token)

        resp = client.get("/beekeeper/profile", headers=headers)
        assert resp.status_code == 403

        resp = client.get("/beekeeper/apiaries", headers=headers)
        assert resp.status_code == 403
    finally:
        db.close()
        _cleanup_user_hierarchy(email)


# ═══════════════════════════════════════════════════════════════════════════
# 2. BEEKEEPER PROFILE TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_create_and_retrieve_beekeeper_profile():
    email = "bk_prof_test1@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9833333331")
        headers = _auth_header(token)

        # Before creation -> 404
        get_before = client.get("/beekeeper/profile", headers=headers)
        assert get_before.status_code == 404

        # Create profile
        payload = {
            "beekeeper_code": "BK-TEST-001",
            "address": "Farm House 12",
            "village": "Madhupur",
            "district": "Deoghar",
            "state": "Jharkhand",
            "pincode": "815353",
            "experience_years": 5,
        }
        create_resp = client.post("/beekeeper/profile", json=payload, headers=headers)
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["beekeeper_code"] == "BK-TEST-001"
        assert data["village"] == "Madhupur"
        assert data["experience_years"] == 5

        # Retrieve profile
        get_after = client.get("/beekeeper/profile", headers=headers)
        assert get_after.status_code == 200
        assert get_after.json()["id"] == data["id"]
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_duplicate_beekeeper_profile_rejected():
    email = "bk_prof_dup@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9833333332")
        headers = _auth_header(token)

        client.post("/beekeeper/profile", json={"address": "First"}, headers=headers)
        second_resp = client.post("/beekeeper/profile", json={"address": "Second"}, headers=headers)
        assert second_resp.status_code == 409
        assert "already exists" in second_resp.json()["detail"].lower()
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_duplicate_beekeeper_code_rejected():
    email1 = "bk_code_1@example.com"
    email2 = "bk_code_2@example.com"
    try:
        _, token1 = _create_user_and_token(email1, "BEEKEEPER", "9833333333")
        _, token2 = _create_user_and_token(email2, "BEEKEEPER", "9833333334")

        client.post(
            "/beekeeper/profile",
            json={"beekeeper_code": "BK-SHARED-CODE"},
            headers=_auth_header(token1),
        )
        resp2 = client.post(
            "/beekeeper/profile",
            json={"beekeeper_code": "BK-SHARED-CODE"},
            headers=_auth_header(token2),
        )
        assert resp2.status_code == 409
        assert "already registered" in resp2.json()["detail"].lower()
    finally:
        _cleanup_user_hierarchy(email1)
        _cleanup_user_hierarchy(email2)


@skip_if_no_db
def test_update_beekeeper_profile():
    email = "bk_prof_update@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9833333335")
        headers = _auth_header(token)

        client.post(
            "/beekeeper/profile",
            json={"village": "Old Village", "experience_years": 2},
            headers=headers,
        )
        update_resp = client.put(
            "/beekeeper/profile",
            json={"village": "New Village", "experience_years": 3},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["village"] == "New Village"
        assert update_resp.json()["experience_years"] == 3
    finally:
        _cleanup_user_hierarchy(email)


# ═══════════════════════════════════════════════════════════════════════════
# 3. APIARY TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_apiary_lifecycle_and_validation():
    email = "bk_apiary_test@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9844444441")
        headers = _auth_header(token)

        # Before profile created -> 400 Bad Request
        bad_resp = client.post(
            "/beekeeper/apiaries", json={"name": "Premature Apiary"}, headers=headers
        )
        assert bad_resp.status_code == 400

        # Create profile
        client.post("/beekeeper/profile", json={}, headers=headers)

        # Invalid GPS coords -> 422
        bad_lat = client.post(
            "/beekeeper/apiaries",
            json={"name": "Bad Lat", "latitude": 95.0, "longitude": 75.0},
            headers=headers,
        )
        assert bad_lat.status_code == 422

        bad_lon = client.post(
            "/beekeeper/apiaries",
            json={"name": "Bad Lon", "latitude": 25.0, "longitude": -185.0},
            headers=headers,
        )
        assert bad_lon.status_code == 422

        # Valid create
        create_resp = client.post(
            "/beekeeper/apiaries",
            json={
                "name": "North Meadow Apiary",
                "location_name": "Sector 4",
                "latitude": 27.2152,
                "longitude": 77.4930,
                "address": "Plot 42, North Meadow",
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        apiary_id = create_resp.json()["id"]
        assert create_resp.json()["name"] == "North Meadow Apiary"

        # List apiaries
        list_resp = client.get("/beekeeper/apiaries", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        # Retrieve apiary
        get_resp = client.get(f"/beekeeper/apiaries/{apiary_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == apiary_id

        # Update apiary
        update_resp = client.put(
            f"/beekeeper/apiaries/{apiary_id}",
            json={"name": "Updated Meadow Apiary"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Meadow Apiary"

        # Delete apiary
        del_resp = client.delete(f"/beekeeper/apiaries/{apiary_id}", headers=headers)
        assert del_resp.status_code == 204

        # Confirm deleted
        get_after_del = client.get(f"/beekeeper/apiaries/{apiary_id}", headers=headers)
        assert get_after_del.status_code == 404
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_cross_beekeeper_apiary_access_rejected():
    email_a = "bk_apiary_a@example.com"
    email_b = "bk_apiary_b@example.com"
    try:
        _, token_a = _create_user_and_token(email_a, "BEEKEEPER", "9844444442")
        _, token_b = _create_user_and_token(email_b, "BEEKEEPER", "9844444443")

        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_a))
        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_b))

        apiary_a = client.post(
            "/beekeeper/apiaries",
            json={"name": "Apiary A"},
            headers=_auth_header(token_a),
        ).json()

        headers_b = _auth_header(token_b)

        # Beekeeper B cannot GET A's apiary
        resp = client.get(f"/beekeeper/apiaries/{apiary_a['id']}", headers=headers_b)
        assert resp.status_code == 404

        # Beekeeper B cannot PUT A's apiary
        resp = client.put(
            f"/beekeeper/apiaries/{apiary_a['id']}",
            json={"name": "Hacked"},
            headers=headers_b,
        )
        assert resp.status_code == 404

        # Beekeeper B cannot DELETE A's apiary
        resp = client.delete(f"/beekeeper/apiaries/{apiary_a['id']}", headers=headers_b)
        assert resp.status_code == 404
    finally:
        _cleanup_user_hierarchy(email_a)
        _cleanup_user_hierarchy(email_b)


@skip_if_no_db
def test_delete_apiary_with_existing_hives_rejected():
    email = "bk_apiary_hive_del@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9844444444")
        headers = _auth_header(token)

        client.post("/beekeeper/profile", json={}, headers=headers)
        apiary = client.post(
            "/beekeeper/apiaries", json={"name": "Apiary with Hives"}, headers=headers
        ).json()

        # Add a hive to the apiary
        client.post(
            f"/beekeeper/apiaries/{apiary['id']}/hives",
            json={"hive_code": "HIVE-01", "hive_type": "Langstroth"},
            headers=headers,
        )

        # Attempt to delete apiary -> must be rejected (400)
        del_resp = client.delete(f"/beekeeper/apiaries/{apiary['id']}", headers=headers)
        assert del_resp.status_code == 400
        assert "existing hives" in del_resp.json()["detail"].lower()
    finally:
        _cleanup_user_hierarchy(email)


# ═══════════════════════════════════════════════════════════════════════════
# 4. HIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_hive_lifecycle_and_scope():
    email = "bk_hive_test@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9855555551")
        headers = _auth_header(token)

        client.post("/beekeeper/profile", json={}, headers=headers)
        apiary = client.post(
            "/beekeeper/apiaries", json={"name": "Hive Test Apiary"}, headers=headers
        ).json()
        apiary_id = apiary["id"]

        # Create hive
        create_resp = client.post(
            f"/beekeeper/apiaries/{apiary_id}/hives",
            json={
                "hive_code": "HIVE-101",
                "hive_type": "Langstroth 10-frame",
                "installation_date": str(date.today()),
                "status": "ACTIVE",
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        hive_id = create_resp.json()["id"]

        # Duplicate hive_code in same apiary -> 409
        dup_resp = client.post(
            f"/beekeeper/apiaries/{apiary_id}/hives",
            json={"hive_code": "HIVE-101", "hive_type": "Top-Bar"},
            headers=headers,
        )
        assert dup_resp.status_code == 409

        # List hives in apiary
        list_resp = client.get(f"/beekeeper/apiaries/{apiary_id}/hives", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        # Retrieve hive
        get_resp = client.get(f"/beekeeper/hives/{hive_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["hive_code"] == "HIVE-101"

        # Update hive
        update_resp = client.put(
            f"/beekeeper/hives/{hive_id}",
            json={"status": "INACTIVE", "hive_type": "Langstroth Modified"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "INACTIVE"
        assert update_resp.json()["hive_type"] == "Langstroth Modified"

        # Delete hive
        del_resp = client.delete(f"/beekeeper/hives/{hive_id}", headers=headers)
        assert del_resp.status_code == 204

        # Confirm deleted
        assert client.get(f"/beekeeper/hives/{hive_id}", headers=headers).status_code == 404
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_cross_beekeeper_hive_access_rejected():
    email_a = "bk_hive_a@example.com"
    email_b = "bk_hive_b@example.com"
    try:
        _, token_a = _create_user_and_token(email_a, "BEEKEEPER", "9855555552")
        _, token_b = _create_user_and_token(email_b, "BEEKEEPER", "9855555553")

        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_a))
        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_b))

        apiary_a = client.post(
            "/beekeeper/apiaries", json={"name": "Apiary A"}, headers=_auth_header(token_a)
        ).json()
        hive_a = client.post(
            f"/beekeeper/apiaries/{apiary_a['id']}/hives",
            json={"hive_code": "H-A1", "hive_type": "Langstroth"},
            headers=_auth_header(token_a),
        ).json()

        headers_b = _auth_header(token_b)

        # B cannot create hive under A's apiary
        resp = client.post(
            f"/beekeeper/apiaries/{apiary_a['id']}/hives",
            json={"hive_code": "H-B1", "hive_type": "Langstroth"},
            headers=headers_b,
        )
        assert resp.status_code == 404

        # B cannot view A's hives
        resp = client.get(f"/beekeeper/apiaries/{apiary_a['id']}/hives", headers=headers_b)
        assert resp.status_code == 404

        # B cannot GET A's hive
        resp = client.get(f"/beekeeper/hives/{hive_a['id']}", headers=headers_b)
        assert resp.status_code == 404

        # B cannot DELETE A's hive
        resp = client.delete(f"/beekeeper/hives/{hive_a['id']}", headers=headers_b)
        assert resp.status_code == 404
    finally:
        _cleanup_user_hierarchy(email_a)
        _cleanup_user_hierarchy(email_b)


@skip_if_no_db
def test_delete_hive_with_recorded_harvests_rejected():
    email = "bk_hive_harv_del@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9855555554")
        headers = _auth_header(token)

        client.post("/beekeeper/profile", json={}, headers=headers)
        apiary = client.post(
            "/beekeeper/apiaries", json={"name": "Harvest Apiary"}, headers=headers
        ).json()
        hive = client.post(
            f"/beekeeper/apiaries/{apiary['id']}/hives",
            json={"hive_code": "H-PROTECTED", "hive_type": "Langstroth"},
            headers=headers,
        ).json()

        # Record a harvest
        client.post(
            f"/beekeeper/hives/{hive['id']}/harvests",
            json={
                "harvest_date": str(date.today()),
                "actual_quantity_kg": 15.0,
                "honey_type": "Mustard",
            },
            headers=headers,
        )

        # Attempt to delete hive -> rejected (400)
        del_resp = client.delete(f"/beekeeper/hives/{hive['id']}", headers=headers)
        assert del_resp.status_code == 400
        assert "recorded harvests" in del_resp.json()["detail"].lower()
    finally:
        _cleanup_user_hierarchy(email)


# ═══════════════════════════════════════════════════════════════════════════
# 5. HONEY HARVEST TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_harvest_lifecycle_and_quantity_validation():
    email = "bk_harvest_test@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9866666661")
        headers = _auth_header(token)

        client.post("/beekeeper/profile", json={}, headers=headers)
        apiary = client.post(
            "/beekeeper/apiaries", json={"name": "Harvest Meadow"}, headers=headers
        ).json()
        hive = client.post(
            f"/beekeeper/apiaries/{apiary['id']}/hives",
            json={"hive_code": "H-HARV", "hive_type": "Langstroth"},
            headers=headers,
        ).json()
        hive_id = hive["id"]

        # Negative actual quantity -> 422
        bad_actual = client.post(
            f"/beekeeper/hives/{hive_id}/harvests",
            json={
                "harvest_date": str(date.today()),
                "actual_quantity_kg": -5.0,
                "honey_type": "Mustard",
            },
            headers=headers,
        )
        assert bad_actual.status_code == 422

        # Negative estimated quantity -> 422
        bad_estimated = client.post(
            f"/beekeeper/hives/{hive_id}/harvests",
            json={
                "harvest_date": str(date.today()),
                "estimated_quantity_kg": -2.0,
                "actual_quantity_kg": 10.0,
                "honey_type": "Mustard",
            },
            headers=headers,
        )
        assert bad_estimated.status_code == 422

        # Successful harvest
        create_resp = client.post(
            f"/beekeeper/hives/{hive_id}/harvests",
            json={
                "harvest_date": str(date.today()),
                "estimated_quantity_kg": 12.0,
                "actual_quantity_kg": 14.5,
                "honey_type": "Mustard",
                "notes": "Excellent harvest; dry climate conditions",
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        harvest_id = create_resp.json()["id"]
        assert create_resp.json()["actual_quantity_kg"] == 14.5
        assert create_resp.json()["estimated_quantity_kg"] == 12.0

        # Retrieve harvest
        get_resp = client.get(f"/beekeeper/harvests/{harvest_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == harvest_id

        # List harvests for hive
        list_resp = client.get(f"/beekeeper/hives/{hive_id}/harvests", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_cross_beekeeper_harvest_access_rejected():
    email_a = "bk_harv_a@example.com"
    email_b = "bk_harv_b@example.com"
    try:
        _, token_a = _create_user_and_token(email_a, "BEEKEEPER", "9866666662")
        _, token_b = _create_user_and_token(email_b, "BEEKEEPER", "9866666663")

        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_a))
        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_b))

        apiary_a = client.post(
            "/beekeeper/apiaries", json={"name": "Apiary A"}, headers=_auth_header(token_a)
        ).json()
        hive_a = client.post(
            f"/beekeeper/apiaries/{apiary_a['id']}/hives",
            json={"hive_code": "H-A", "hive_type": "Langstroth"},
            headers=_auth_header(token_a),
        ).json()
        harv_a = client.post(
            f"/beekeeper/hives/{hive_a['id']}/harvests",
            json={
                "harvest_date": str(date.today()),
                "actual_quantity_kg": 20.0,
                "honey_type": "Acacia",
            },
            headers=_auth_header(token_a),
        ).json()

        headers_b = _auth_header(token_b)

        # B cannot record harvest on A's hive
        resp = client.post(
            f"/beekeeper/hives/{hive_a['id']}/harvests",
            json={
                "harvest_date": str(date.today()),
                "actual_quantity_kg": 5.0,
                "honey_type": "Acacia",
            },
            headers=headers_b,
        )
        assert resp.status_code == 404

        # B cannot retrieve A's harvest
        resp = client.get(f"/beekeeper/harvests/{harv_a['id']}", headers=headers_b)
        assert resp.status_code == 404
    finally:
        _cleanup_user_hierarchy(email_a)
        _cleanup_user_hierarchy(email_b)


# ═══════════════════════════════════════════════════════════════════════════
# 6. HONEY BATCH TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_batch_creation_and_capacity_limits():
    email = "bk_batch_test@example.com"
    try:
        _, token = _create_user_and_token(email, "BEEKEEPER", "9877777771")
        headers = _auth_header(token)

        client.post("/beekeeper/profile", json={}, headers=headers)
        apiary = client.post(
            "/beekeeper/apiaries", json={"name": "Batch Apiary"}, headers=headers
        ).json()
        hive = client.post(
            f"/beekeeper/apiaries/{apiary['id']}/hives",
            json={"hive_code": "H-BATCH", "hive_type": "Langstroth"},
            headers=headers,
        ).json()

        # 25.0 kg total harvest
        harvest = client.post(
            f"/beekeeper/hives/{hive['id']}/harvests",
            json={
                "harvest_date": str(date.today()),
                "actual_quantity_kg": 25.0,
                "honey_type": "Multifloral",
            },
            headers=headers,
        ).json()
        harvest_id = harvest["id"]

        # Negative batch quantity -> 422
        bad_qty = client.post(
            f"/beekeeper/harvests/{harvest_id}/batches",
            json={
                "batch_code": "BATCH-NEG",
                "batch_date": str(date.today()),
                "quantity_kg": -1.0,
                "honey_type": "Multifloral",
            },
            headers=headers,
        )
        assert bad_qty.status_code == 422

        # Quantity exceeding harvest capacity (30 kg > 25 kg) -> 400
        exceed_qty = client.post(
            f"/beekeeper/harvests/{harvest_id}/batches",
            json={
                "batch_code": "BATCH-EXCEED",
                "batch_date": str(date.today()),
                "quantity_kg": 30.0,
                "honey_type": "Multifloral",
            },
            headers=headers,
        )
        assert exceed_qty.status_code == 400
        assert "exceeds available" in exceed_qty.json()["detail"].lower()

        # Batch 1: 15.0 kg (valid, 10.0 kg remaining)
        b1 = client.post(
            f"/beekeeper/harvests/{harvest_id}/batches",
            json={
                "batch_code": "BATCH-001",
                "batch_date": str(date.today()),
                "quantity_kg": 15.0,
                "honey_type": "Multifloral",
            },
            headers=headers,
        )
        assert b1.status_code == 201
        batch1_id = b1.json()["id"]

        # Duplicate batch_code -> 409
        dup_code = client.post(
            f"/beekeeper/harvests/{harvest_id}/batches",
            json={
                "batch_code": "BATCH-001",
                "batch_date": str(date.today()),
                "quantity_kg": 5.0,
                "honey_type": "Multifloral",
            },
            headers=headers,
        )
        assert dup_code.status_code == 409

        # Batch 2: 10.0 kg (valid, 0.0 kg remaining)
        b2 = client.post(
            f"/beekeeper/harvests/{harvest_id}/batches",
            json={
                "batch_code": "BATCH-002",
                "batch_date": str(date.today()),
                "quantity_kg": 10.0,
                "honey_type": "Multifloral",
            },
            headers=headers,
        )
        assert b2.status_code == 201

        # Batch 3: 1.0 kg (exceeds 0 remaining) -> 400
        b3 = client.post(
            f"/beekeeper/harvests/{harvest_id}/batches",
            json={
                "batch_code": "BATCH-003",
                "batch_date": str(date.today()),
                "quantity_kg": 1.0,
                "honey_type": "Multifloral",
            },
            headers=headers,
        )
        assert b3.status_code == 400

        # List batches
        list_resp = client.get("/beekeeper/batches", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 2

        # Retrieve batch
        get_b1 = client.get(f"/beekeeper/batches/{batch1_id}", headers=headers)
        assert get_b1.status_code == 200
        assert get_b1.json()["batch_code"] == "BATCH-001"

        # Update batch status to PROCESSING
        up_resp = client.put(
            f"/beekeeper/batches/{batch1_id}",
            json={"status": "PROCESSING"},
            headers=headers,
        )
        assert up_resp.status_code == 200
        assert up_resp.json()["status"] == "PROCESSING"

        # Update batch quantity beyond remaining capacity (15 kg -> 18 kg, but only 10 kg allocated to b2 => total 28 > 25)
        up_bad_qty = client.put(
            f"/beekeeper/batches/{batch1_id}",
            json={"quantity_kg": 18.0},
            headers=headers,
        )
        assert up_bad_qty.status_code == 400
    finally:
        _cleanup_user_hierarchy(email)


@skip_if_no_db
def test_cross_beekeeper_batch_access_rejected():
    email_a = "bk_batch_a@example.com"
    email_b = "bk_batch_b@example.com"
    try:
        _, token_a = _create_user_and_token(email_a, "BEEKEEPER", "9877777772")
        _, token_b = _create_user_and_token(email_b, "BEEKEEPER", "9877777773")

        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_a))
        client.post("/beekeeper/profile", json={}, headers=_auth_header(token_b))

        apiary_a = client.post(
            "/beekeeper/apiaries", json={"name": "Apiary A"}, headers=_auth_header(token_a)
        ).json()
        hive_a = client.post(
            f"/beekeeper/apiaries/{apiary_a['id']}/hives",
            json={"hive_code": "H-A", "hive_type": "Langstroth"},
            headers=_auth_header(token_a),
        ).json()
        harv_a = client.post(
            f"/beekeeper/hives/{hive_a['id']}/harvests",
            json={
                "harvest_date": str(date.today()),
                "actual_quantity_kg": 50.0,
                "honey_type": "Eucalyptus",
            },
            headers=_auth_header(token_a),
        ).json()
        batch_a = client.post(
            f"/beekeeper/harvests/{harv_a['id']}/batches",
            json={
                "batch_code": "BATCH-A-01",
                "batch_date": str(date.today()),
                "quantity_kg": 20.0,
                "honey_type": "Eucalyptus",
            },
            headers=_auth_header(token_a),
        ).json()

        headers_b = _auth_header(token_b)

        # B cannot create batch from A's harvest
        resp = client.post(
            f"/beekeeper/harvests/{harv_a['id']}/batches",
            json={
                "batch_code": "BATCH-B-ATTEMPT",
                "batch_date": str(date.today()),
                "quantity_kg": 5.0,
                "honey_type": "Eucalyptus",
            },
            headers=headers_b,
        )
        assert resp.status_code == 404

        # B cannot GET A's batch
        resp = client.get(f"/beekeeper/batches/{batch_a['id']}", headers=headers_b)
        assert resp.status_code == 404

        # B cannot PUT A's batch
        resp = client.put(
            f"/beekeeper/batches/{batch_a['id']}",
            json={"status": "SOLD"},
            headers=headers_b,
        )
        assert resp.status_code == 404
    finally:
        _cleanup_user_hierarchy(email_a)
        _cleanup_user_hierarchy(email_b)


# ═══════════════════════════════════════════════════════════════════════════
# 7. DATABASE FOREIGN KEY INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_foreign_key_restricts_parent_deletion_directly_in_database():
    """Verify in the database that ondelete='RESTRICT' blocks deleting parents with active children."""
    email = "fk_restrict_test@example.com"
    db: Session = SessionLocal()
    try:
        user = User(
            full_name="FK Test User",
            email=email,
            phone="9888888881",
            password_hash=hash_password("Pass123!"),
            role="BEEKEEPER",
            is_active=True,
        )
        db.add(user)
        db.commit()

        profile = BeekeeperProfile(
            user_id=user.id,
            beekeeper_code="BK-FK-TEST",
        )
        db.add(profile)
        db.commit()

        # Attempting to delete user directly without removing profile must raise IntegrityError
        db.delete(user)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
        _cleanup_user_hierarchy(email)
