"""
Comprehensive authentication and RBAC test suite.

Covers:
  Registration:
    - BUYER registration succeeds
    - BEEKEEPER registration succeeds
    - KVIC_ADMIN public registration is BLOCKED (HTTP 403)
    - duplicate email rejection (HTTP 409)
    - password is hashed and never stored as plaintext
    - response never contains password_hash

  Login:
    - successful login returns JWT + user info
    - invalid password → HTTP 401
    - non-existent email → HTTP 401
    - inactive user → HTTP 403
    - existing KVIC_ADMIN can still log in

  /auth/me:
    - valid token returns current user
    - missing token → HTTP 403 (HTTPBearer auto_error)
    - invalid/tampered token → HTTP 401

  RBAC:
    - BUYER  can access /auth/test/buyer only
    - BEEKEEPER can access /auth/test/beekeeper only
    - KVIC_ADMIN can access /auth/test/kvic-admin only
    - BUYER cannot access KVIC endpoint
    - BEEKEEPER cannot access KVIC endpoint
    - KVIC_ADMIN cannot access BUYER-only endpoint
    - Cross-role access → HTTP 403
    - Unauthenticated access → HTTP 403

These tests use the FastAPI TestClient (synchronous) with a real database.
Each test function that creates data cleans up after itself via try/finally.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crud.user import get_user_by_email
from app.db import SessionLocal, check_db_connection
from app.main import app
from app.models.user import User

client = TestClient(app)

# ── Database availability guard ────────────────────────────────────────────
skip_if_no_db = pytest.mark.skipif(
    not check_db_connection(),
    reason="PostgreSQL is not reachable — skipping auth integration tests.",
)


# ── Helpers ────────────────────────────────────────────────────────────────
def _cleanup_email(email: str) -> None:
    """Delete the user with *email* from the database after each test."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_active = True   # re-activate so we can delete cleanly
            db.commit()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _register(payload: dict):
    return client.post("/auth/register", json=payload)


def _login(email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_token(payload: dict) -> str:
    """
    Register the user (ignoring 409 if already exists) then log in and return
    the access token. The caller is responsible for cleanup via _cleanup_email.

    NOTE: This helper only works for BUYER and BEEKEEPER. KVIC_ADMIN cannot
    self-register, so use _provision_kvic_admin_and_login instead.
    """
    resp = _register(payload)
    assert resp.status_code in (201, 409), (
        f"Unexpected register status: {resp.status_code} — {resp.text}"
    )
    login_resp = _login(payload["email"], payload["password"])
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    return login_resp.json()["access_token"]


def _provision_kvic_admin(email: str, password: str, full_name: str = "Test KVIC Admin") -> None:
    """
    Insert a KVIC_ADMIN user directly in the database (bypassing the API).

    This simulates how a real admin provisioning system would work. The
    public registration endpoint blocks KVIC_ADMIN, so tests that need a
    KVIC_ADMIN user must use this helper.
    """
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return  # already provisioned from a previous test
        user = User(
            full_name=full_name,
            email=email,
            phone="9000000099",
            password_hash=hash_password(password),
            role="KVIC_ADMIN",
            is_active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def _kvic_token(email: str = "testkvic@example.com", password: str = "SecurePass123") -> str:
    """Provision a KVIC_ADMIN via DB, log in via API, return token."""
    _provision_kvic_admin(email, password)
    login_resp = _login(email, password)
    assert login_resp.status_code == 200, f"KVIC login failed: {login_resp.text}"
    return login_resp.json()["access_token"]


# ── Test payloads (RFC 5321-safe domains) ─────────────────────────────────
BUYER_PAYLOAD = {
    "full_name": "Test Buyer",
    "email": "testbuyer@example.com",
    "phone": "9000000001",
    "password": "SecurePass123",
    "role": "BUYER",
}
BEEKEEPER_PAYLOAD = {
    "full_name": "Test Beekeeper",
    "email": "testbeekeeper@example.com",
    "phone": "9000000002",
    "password": "SecurePass123",
    "role": "BEEKEEPER",
}
KVIC_PAYLOAD = {
    "full_name": "Test KVIC Admin",
    "email": "testkvic@example.com",
    "phone": "9000000003",
    "password": "SecurePass123",
    "role": "KVIC_ADMIN",
}


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_register_buyer_success():
    try:
        resp = _register(BUYER_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == BUYER_PAYLOAD["email"]
        assert data["role"] == "BUYER"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_register_beekeeper_success():
    try:
        resp = _register(BEEKEEPER_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["role"] == "BEEKEEPER"
    finally:
        _cleanup_email(BEEKEEPER_PAYLOAD["email"])


@skip_if_no_db
def test_register_kvic_admin_is_blocked():
    """Public registration must reject KVIC_ADMIN with HTTP 403."""
    resp = _register(KVIC_PAYLOAD)
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert "KVIC_ADMIN" in detail
    assert "not allowed" in detail.lower()


@skip_if_no_db
def test_register_duplicate_email_returns_409():
    try:
        first = _register(BUYER_PAYLOAD)
        assert first.status_code == 201
        second = _register(BUYER_PAYLOAD)  # same email again
        assert second.status_code == 409
        assert "already exists" in second.json()["detail"].lower()
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_register_response_never_contains_password_hash():
    try:
        resp = _register(BUYER_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert "password_hash" not in data
        assert "password" not in data
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_password_is_stored_as_bcrypt_hash_not_plaintext():
    """Confirm the DB row contains a bcrypt hash, never the plaintext password."""
    try:
        _register(BUYER_PAYLOAD)
        db: Session = SessionLocal()
        try:
            user = get_user_by_email(db, BUYER_PAYLOAD["email"])
            assert user is not None
            assert user.password_hash.startswith("$2b$")        # bcrypt signature
            assert user.password_hash != BUYER_PAYLOAD["password"]  # not plaintext
        finally:
            db.close()
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_register_invalid_role_returns_422():
    payload = {**BUYER_PAYLOAD, "role": "SUPERUSER"}
    resp = _register(payload)
    assert resp.status_code == 422


@skip_if_no_db
def test_register_missing_email_returns_422():
    payload = {k: v for k, v in BUYER_PAYLOAD.items() if k != "email"}
    resp = _register(payload)
    assert resp.status_code == 422


@skip_if_no_db
def test_register_short_password_returns_422():
    payload = {**BUYER_PAYLOAD, "password": "short"}
    resp = _register(payload)
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# LOGIN TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_login_success_returns_token_and_user():
    try:
        _register(BUYER_PAYLOAD)
        resp = _login(BUYER_PAYLOAD["email"], BUYER_PAYLOAD["password"])
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == BUYER_PAYLOAD["email"]
        assert "password_hash" not in data["user"]
        assert "password" not in data["user"]
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_login_wrong_password_returns_401():
    try:
        _register(BUYER_PAYLOAD)
        resp = _login(BUYER_PAYLOAD["email"], "WrongPassword!")
        assert resp.status_code == 401
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_login_nonexistent_email_returns_401():
    resp = _login("nobody@example.com", "AnyPassword1")
    assert resp.status_code == 401


@skip_if_no_db
def test_login_inactive_user_returns_403():
    try:
        _register(BUYER_PAYLOAD)
        db: Session = SessionLocal()
        try:
            user = get_user_by_email(db, BUYER_PAYLOAD["email"])
            assert user is not None
            user.is_active = False
            db.commit()
        finally:
            db.close()
        resp = _login(BUYER_PAYLOAD["email"], BUYER_PAYLOAD["password"])
        assert resp.status_code == 403
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_existing_kvic_admin_can_login():
    """A KVIC_ADMIN provisioned via DB (not public registration) can still log in."""
    try:
        _provision_kvic_admin(KVIC_PAYLOAD["email"], KVIC_PAYLOAD["password"])
        resp = _login(KVIC_PAYLOAD["email"], KVIC_PAYLOAD["password"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role"] == "KVIC_ADMIN"
        assert "password_hash" not in data["user"]
    finally:
        _cleanup_email(KVIC_PAYLOAD["email"])


# ═══════════════════════════════════════════════════════════════════════════
# /auth/me TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_me_returns_current_user():
    try:
        _register(BUYER_PAYLOAD)
        token = _login(BUYER_PAYLOAD["email"], BUYER_PAYLOAD["password"]).json()["access_token"]
        resp = client.get("/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == BUYER_PAYLOAD["email"]
        assert "password_hash" not in data
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_me_without_token_returns_403():
    resp = client.get("/auth/me")
    assert resp.status_code == 403


@skip_if_no_db
def test_me_with_invalid_token_returns_401():
    resp = client.get("/auth/me", headers=_auth_header("this.is.not.a.valid.jwt"))
    assert resp.status_code == 401


@skip_if_no_db
def test_me_with_tampered_token_returns_401():
    try:
        _register(BUYER_PAYLOAD)
        token = _login(BUYER_PAYLOAD["email"], BUYER_PAYLOAD["password"]).json()["access_token"]
        tampered = token[:-5] + "XXXXX"
        resp = client.get("/auth/me", headers=_auth_header(tampered))
        assert resp.status_code == 401
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


# ═══════════════════════════════════════════════════════════════════════════
# RBAC TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_buyer_can_access_buyer_endpoint():
    try:
        token = _get_token(BUYER_PAYLOAD)
        resp = client.get("/auth/test/buyer", headers=_auth_header(token))
        assert resp.status_code == 200
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_buyer_cannot_access_beekeeper_endpoint():
    try:
        token = _get_token(BUYER_PAYLOAD)
        resp = client.get("/auth/test/beekeeper", headers=_auth_header(token))
        assert resp.status_code == 403
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_buyer_cannot_access_kvic_admin_endpoint():
    try:
        token = _get_token(BUYER_PAYLOAD)
        resp = client.get("/auth/test/kvic-admin", headers=_auth_header(token))
        assert resp.status_code == 403
    finally:
        _cleanup_email(BUYER_PAYLOAD["email"])


@skip_if_no_db
def test_beekeeper_can_access_beekeeper_endpoint():
    try:
        token = _get_token(BEEKEEPER_PAYLOAD)
        resp = client.get("/auth/test/beekeeper", headers=_auth_header(token))
        assert resp.status_code == 200
    finally:
        _cleanup_email(BEEKEEPER_PAYLOAD["email"])


@skip_if_no_db
def test_beekeeper_cannot_access_buyer_endpoint():
    try:
        token = _get_token(BEEKEEPER_PAYLOAD)
        resp = client.get("/auth/test/buyer", headers=_auth_header(token))
        assert resp.status_code == 403
    finally:
        _cleanup_email(BEEKEEPER_PAYLOAD["email"])


@skip_if_no_db
def test_beekeeper_cannot_access_kvic_admin_endpoint():
    try:
        token = _get_token(BEEKEEPER_PAYLOAD)
        resp = client.get("/auth/test/kvic-admin", headers=_auth_header(token))
        assert resp.status_code == 403
    finally:
        _cleanup_email(BEEKEEPER_PAYLOAD["email"])


@skip_if_no_db
def test_kvic_admin_can_access_kvic_admin_endpoint():
    """Existing KVIC_ADMIN (provisioned via DB) can access KVIC-protected endpoint."""
    try:
        token = _kvic_token(KVIC_PAYLOAD["email"], KVIC_PAYLOAD["password"])
        resp = client.get("/auth/test/kvic-admin", headers=_auth_header(token))
        assert resp.status_code == 200
    finally:
        _cleanup_email(KVIC_PAYLOAD["email"])


@skip_if_no_db
def test_kvic_admin_cannot_access_buyer_endpoint():
    """KVIC_ADMIN must NOT be able to access the BUYER-only endpoint."""
    try:
        token = _kvic_token(KVIC_PAYLOAD["email"], KVIC_PAYLOAD["password"])
        resp = client.get("/auth/test/buyer", headers=_auth_header(token))
        assert resp.status_code == 403
    finally:
        _cleanup_email(KVIC_PAYLOAD["email"])


@skip_if_no_db
def test_kvic_admin_cannot_access_beekeeper_endpoint():
    try:
        token = _kvic_token(KVIC_PAYLOAD["email"], KVIC_PAYLOAD["password"])
        resp = client.get("/auth/test/beekeeper", headers=_auth_header(token))
        assert resp.status_code == 403
    finally:
        _cleanup_email(KVIC_PAYLOAD["email"])


@skip_if_no_db
def test_unauthenticated_access_to_rbac_endpoints_returns_403():
    """All RBAC test endpoints must reject requests without a token."""
    for path in ["/auth/test/buyer", "/auth/test/beekeeper", "/auth/test/kvic-admin"]:
        resp = client.get(path)
        assert resp.status_code == 403, f"Expected 403 for {path}, got {resp.status_code}"
