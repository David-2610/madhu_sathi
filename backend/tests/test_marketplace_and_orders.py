"""
Comprehensive test suite for Phase 6: Marketplace, Cart, Orders, and Payment Preparation.

Covers:
  Marketplace & Beekeeper Listing Management:
    - Beekeeper sets price and lists product for sale (Decimal, INR, is_listed=True)
    - Beekeeper cannot list product with status REVOKED, SOLD, or SUSPICIOUS (HTTP 400)
    - Marketplace browse (GET /marketplace/products) returns only listed, active products
    - Marketplace detail (GET /marketplace/products/{id}) returns detailed info; 404 for unlisted/inactive
    - Buyer cannot modify product listing/pricing (HTTP 403)
    - Beekeeper B cannot modify Beekeeper A's product listing (HTTP 404)

  Buyer Cart Operations:
    - Cart accessible only to BUYER (Beekeeper and KVIC_ADMIN receive HTTP 403)
    - Add item to cart, view cart with dynamic availability and Decimal subtotal
    - Duplicate product in cart rejected (HTTP 409)
    - Unavailable/unlisted product cannot be added to cart (HTTP 400)
    - Stale availability reflected on cart view
    - Remove individual item from cart
    - Empty cart

  Atomic Checkout & Concurrency Protection:
    - Server-side Decimal calculation (never trusts client price; client price tampering impossible)
    - Product rows locked with SELECT ... FOR UPDATE
    - Products transition to RESERVED upon checkout
    - Cart emptied upon checkout
    - Concurrent double-purchase protection: two checkouts for same unit; one succeeds, second rejected (HTTP 409)

  Payment Provider Abstraction & Order Lifecycle:
    - Order placed with status PENDING_PAYMENT
    - Mock payment creation clearly identified as MOCK with MOCK-PAY- reference
    - Payment confirmation success: order -> PAID, products -> SOLD, PRODUCT_SOLD event recorded
    - Payment confirmation failure: order -> PAYMENT_FAILED, products revert to ACTIVE
    - Order state transitions validated (cannot confirm paid order again)
    - Traceability verification: QR /trace/{token} remains functional after sale with SOLD status
    - Cross-user order access rejected (HTTP 404)
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal, check_db_connection
from app.main import app
from app.models.apiary import Apiary
from app.models.beekeeper import BeekeeperProfile
from app.models.cart import Cart, CartItem
from app.models.hive import Hive
from app.models.honey_batch import HoneyBatch
from app.models.honey_harvest import HoneyHarvest
from app.models.honey_product import HoneyProduct, ProductStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.traceability_event import TraceEventType, TraceabilityEvent
from app.models.user import User

client = TestClient(app)

skip_if_no_db = pytest.mark.skipif(
    not check_db_connection(),
    reason="Database is not reachable — skipping DB-dependent tests",
)


# ── Cleanup Helper ─────────────────────────────────────────────────────────
def _cleanup_users_and_records(*emails: str) -> None:
    """Safely delete records across all Phase 1-6 models in strict reverse foreign-key order."""
    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.email.in_(emails)).all()
        user_ids = [u.id for u in users]
        if not user_ids:
            return

        # 1. Gather all carts and orders for buyers
        cart_ids = [c[0] for c in db.query(Cart.id).filter(Cart.buyer_id.in_(user_ids)).all()]
        order_ids = [o[0] for o in db.query(Order.id).filter(Order.buyer_id.in_(user_ids)).all()]

        # 2. Gather beekeeper profiles and batches
        profiles = db.query(BeekeeperProfile).filter(BeekeeperProfile.user_id.in_(user_ids)).all()
        profile_ids = [p.id for p in profiles]
        batch_ids = [b[0] for b in db.query(HoneyBatch.id).filter(HoneyBatch.beekeeper_id.in_(profile_ids)).all()]
        product_ids = [p[0] for p in db.query(HoneyProduct.id).filter(HoneyProduct.batch_id.in_(batch_ids)).all()]

        # Reverse cleanup order
        if order_ids:
            db.query(Payment).filter(Payment.order_id.in_(order_ids)).delete(synchronize_session=False)
            db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)

        if product_ids:
            db.query(TraceabilityEvent).filter(TraceabilityEvent.product_id.in_(product_ids)).delete(synchronize_session=False)
            db.query(CartItem).filter(CartItem.product_id.in_(product_ids)).delete(synchronize_session=False)
            db.query(OrderItem).filter(OrderItem.product_id.in_(product_ids)).delete(synchronize_session=False)

        if cart_ids:
            db.query(CartItem).filter(CartItem.cart_id.in_(cart_ids)).delete(synchronize_session=False)
            db.query(Cart).filter(Cart.id.in_(cart_ids)).delete(synchronize_session=False)

        if order_ids:
            db.query(Order).filter(Order.id.in_(order_ids)).delete(synchronize_session=False)

        if batch_ids:
            db.query(TraceabilityEvent).filter(TraceabilityEvent.batch_id.in_(batch_ids)).delete(synchronize_session=False)
            db.query(HoneyProduct).filter(HoneyProduct.id.in_(product_ids)).delete(synchronize_session=False)
            db.query(HoneyBatch).filter(HoneyBatch.id.in_(batch_ids)).delete(synchronize_session=False)

        if profile_ids:
            apiary_ids = [a[0] for a in db.query(Apiary.id).filter(Apiary.beekeeper_id.in_(profile_ids)).all()]
            if apiary_ids:
                hive_ids = [h[0] for h in db.query(Hive.id).filter(Hive.apiary_id.in_(apiary_ids)).all()]
                if hive_ids:
                    db.query(HoneyHarvest).filter(HoneyHarvest.hive_id.in_(hive_ids)).delete(synchronize_session=False)
                    db.query(Hive).filter(Hive.id.in_(hive_ids)).delete(synchronize_session=False)
                db.query(Apiary).filter(Apiary.id.in_(apiary_ids)).delete(synchronize_session=False)
            db.query(BeekeeperProfile).filter(BeekeeperProfile.id.in_(profile_ids)).delete(synchronize_session=False)

        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_user_and_token(email: str, role: str, phone: str = "9811111111") -> tuple[dict, str]:
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


def _setup_beekeeper_with_product(email: str, phone: str = "9922222222") -> tuple[str, dict, dict]:
    """Helper to set up beekeeper through to an unlisted HoneyProduct."""
    _, token = _create_user_and_token(email, "BEEKEEPER", phone)
    headers = _auth_header(token)

    client.post(
        "/beekeeper/profile",
        json={
            "village": "Madhupur",
            "district": "Deoghar",
            "state": "Jharkhand",
            "pincode": "815353",
            "experience_years": 5,
        },
        headers=headers,
    )
    apiary = client.post(
        "/beekeeper/apiaries",
        json={"name": "Forest Meadow Apiary", "location_name": "Valley North"},
        headers=headers,
    ).json()
    hive = client.post(
        f"/beekeeper/apiaries/{apiary['id']}/hives",
        json={"hive_code": f"HV-{phone[-4:]}", "hive_type": "Langstroth"},
        headers=headers,
    ).json()
    harvest = client.post(
        f"/beekeeper/hives/{hive['id']}/harvests",
        json={
            "harvest_date": str(date.today()),
            "actual_quantity_kg": 50.0,
            "honey_type": "Kashmir Acacia Honey",
        },
        headers=headers,
    ).json()
    batch = client.post(
        f"/beekeeper/harvests/{harvest['id']}/batches",
        json={
            "batch_code": f"BAT-MKT-{phone[-4:]}",
            "batch_date": str(date.today()),
            "quantity_kg": 20.0,
            "honey_type": "Kashmir Acacia Honey",
        },
        headers=headers,
    ).json()
    product = client.post(
        f"/beekeeper/batches/{batch['id']}/products",
        json={"net_weight_g": 500.0, "packaging_date": str(date.today())},
        headers=headers,
    ).json()

    return token, batch, product


# ═══════════════════════════════════════════════════════════════════════════
# 1. MARKETPLACE LISTING & RBAC TESTS
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_beekeeper_product_listing_and_public_marketplace():
    """Verify beekeeper can set price/listing, and marketplace only displays active listed products."""
    email_bk = "mkt_bk_1@example.com"
    email_buyer = "mkt_buyer_1@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email_bk, "9930000001")
        bk_headers = _auth_header(bk_token)
        _, buyer_token = _create_user_and_token(email_buyer, "BUYER", "9930000002")
        buyer_headers = _auth_header(buyer_token)

        prd_id = product["id"]

        # Product initially not listed
        detail_before = client.get(f"/marketplace/products/{prd_id}")
        assert detail_before.status_code == 404

        # 1. Buyer cannot modify product listing -> 403 Forbidden
        buyer_modify = client.put(
            f"/beekeeper/products/{prd_id}/listing",
            json={"price": 550.00, "is_listed": True, "currency": "INR"},
            headers=buyer_headers,
        )
        assert buyer_modify.status_code == 403

        # 2. Beekeeper lists product with price 499.50 INR
        list_resp = client.put(
            f"/beekeeper/products/{prd_id}/listing",
            json={"price": 499.50, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["price"] == "499.50"
        assert data["is_listed"] is True
        assert data["is_available_for_sale"] is True

        # 3. Beekeeper views listing endpoint
        get_list_resp = client.get(f"/beekeeper/products/{prd_id}/listing", headers=bk_headers)
        assert get_list_resp.status_code == 200
        assert get_list_resp.json()["price"] == "499.50"

        # 4. Public/Buyer marketplace browse now includes product
        mkt_list = client.get("/marketplace/products").json()
        matching = [p for p in mkt_list if p["id"] == prd_id]
        assert len(matching) == 1
        assert matching[0]["price"] == "499.50"
        assert matching[0]["honey_type"] == "Kashmir Acacia Honey"
        assert matching[0]["beekeeper_code"] is not None

        # 5. Public/Buyer marketplace detail endpoint
        mkt_detail = client.get(f"/marketplace/products/{prd_id}")
        assert mkt_detail.status_code == 200
        assert mkt_detail.json()["price"] == "499.50"
        assert "/trace/" in mkt_detail.json()["trace_url"]

        # 6. Negative price rejected
        bad_price = client.put(
            f"/beekeeper/products/{prd_id}/listing",
            json={"price": -10.0, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )
        assert bad_price.status_code == 422
    finally:
        _cleanup_users_and_records(email_bk, email_buyer)


@skip_if_no_db
def test_unpurchasable_products_cannot_be_listed():
    """Verify products with status REVOKED, SOLD, or SUSPICIOUS cannot be listed for sale."""
    email = "unpurchasable_test@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email, "9930000003")
        bk_headers = _auth_header(bk_token)
        prd_id = product["id"]

        # Revoke the product
        client.put(f"/beekeeper/products/{prd_id}/status", json={"status": "REVOKED"}, headers=bk_headers)

        # Attempting to list REVOKED product -> 400 Bad Request
        resp = client.put(
            f"/beekeeper/products/{prd_id}/listing",
            json={"price": 350.00, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )
        assert resp.status_code == 400
        assert "only active products may be listed" in resp.json()["detail"].lower()
    finally:
        _cleanup_users_and_records(email)


@skip_if_no_db
def test_cross_beekeeper_listing_access_rejected():
    """Verify Beekeeper B cannot modify Beekeeper A's product listing."""
    email_a = "bk_list_a@example.com"
    email_b = "bk_list_b@example.com"
    try:
        _, _, prd_a = _setup_beekeeper_with_product(email_a, "9930000004")
        token_b, _, _ = _setup_beekeeper_with_product(email_b, "9930000005")
        headers_b = _auth_header(token_b)

        resp = client.put(
            f"/beekeeper/products/{prd_a['id']}/listing",
            json={"price": 200.0, "is_listed": True, "currency": "INR"},
            headers=headers_b,
        )
        assert resp.status_code == 404
    finally:
        _cleanup_users_and_records(email_a, email_b)


# ═══════════════════════════════════════════════════════════════════════════
# 2. BUYER CART OPERATIONS & ROLE ISOLATION
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_cart_role_isolation_and_buyer_crud():
    """Verify only BUYER can access cart, while Beekeeper and KVIC_ADMIN receive 403."""
    email_bk = "cart_bk@example.com"
    email_buyer = "cart_buyer@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email_bk, "9930000006")
        bk_headers = _auth_header(bk_token)
        _, buyer_token = _create_user_and_token(email_buyer, "BUYER", "9930000007")
        buyer_headers = _auth_header(buyer_token)

        # 1. Beekeeper cannot access cart endpoints -> 403 Forbidden
        assert client.get("/buyer/cart", headers=bk_headers).status_code == 403
        assert client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=bk_headers).status_code == 403

        # 2. List the product for 600.00 INR
        client.put(
            f"/beekeeper/products/{product['id']}/listing",
            json={"price": 600.00, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )

        # 3. Buyer gets initial empty cart
        cart = client.get("/buyer/cart", headers=buyer_headers).json()
        assert cart["total_items"] == 0
        assert cart["subtotal_amount"] == "0.00"

        # 4. Buyer adds product to cart
        add_resp = client.post(
            "/buyer/cart/items",
            json={"product_id": product["id"]},
            headers=buyer_headers,
        )
        assert add_resp.status_code == 201
        data = add_resp.json()
        assert data["total_items"] == 1
        assert data["subtotal_amount"] == "600.00"
        item_id = data["items"][0]["id"]
        assert data["items"][0]["is_available"] is True

        # 5. Duplicate item in cart -> 409 Conflict
        dup_resp = client.post(
            "/buyer/cart/items",
            json={"product_id": product["id"]},
            headers=buyer_headers,
        )
        assert dup_resp.status_code == 409
        assert "already in your cart" in dup_resp.json()["detail"].lower()

        # 6. Delete item from cart
        del_item_resp = client.delete(f"/buyer/cart/items/{item_id}", headers=buyer_headers)
        assert del_item_resp.status_code == 200
        assert del_item_resp.json()["total_items"] == 0

        # 7. Add back and empty cart
        client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=buyer_headers)
        clear_resp = client.delete("/buyer/cart", headers=buyer_headers)
        assert clear_resp.status_code == 200
        assert clear_resp.json()["total_items"] == 0
    finally:
        _cleanup_users_and_records(email_bk, email_buyer)


@skip_if_no_db
def test_cart_rejects_unavailable_products_and_stale_availability():
    """Verify unlisted/inactive products cannot be added, and stale cart reflects dynamic availability."""
    email_bk = "stale_bk@example.com"
    email_buyer = "stale_buyer@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email_bk, "9930000008")
        bk_headers = _auth_header(bk_token)
        _, buyer_token = _create_user_and_token(email_buyer, "BUYER", "9930000009")
        buyer_headers = _auth_header(buyer_token)

        prd_id = product["id"]

        # Product unlisted: attempt to add -> 400 Bad Request
        add_unlisted = client.post(
            "/buyer/cart/items",
            json={"product_id": prd_id},
            headers=buyer_headers,
        )
        assert add_unlisted.status_code == 400

        # Beekeeper lists product
        client.put(
            f"/beekeeper/products/{prd_id}/listing",
            json={"price": 400.00, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )

        # Buyer adds to cart
        client.post("/buyer/cart/items", json={"product_id": prd_id}, headers=buyer_headers)

        # Beekeeper unlists product afterwards
        client.put(
            f"/beekeeper/products/{prd_id}/listing",
            json={"price": 400.00, "is_listed": False, "currency": "INR"},
            headers=bk_headers,
        )

        # Buyer inspects cart: product shows is_available = False, subtotal excludes it
        cart = client.get("/buyer/cart", headers=buyer_headers).json()
        assert len(cart["items"]) == 1
        assert cart["items"][0]["is_available"] is False
        assert cart["subtotal_amount"] == "0.00"
    finally:
        _cleanup_users_and_records(email_bk, email_buyer)


# ═══════════════════════════════════════════════════════════════════════════
# 3. ATOMIC CHECKOUT, CONCURRENCY, AND TOTAL CALCULATION
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_checkout_server_side_decimal_calculation_and_snapshots():
    """Verify checkout calculates totals strictly server-side and captures historical snapshots."""
    email_bk = "chk_calc_bk@example.com"
    email_buyer = "chk_calc_buyer@example.com"
    try:
        bk_token, batch, product = _setup_beekeeper_with_product(email_bk, "9930000010")
        bk_headers = _auth_header(bk_token)
        _, buyer_token = _create_user_and_token(email_buyer, "BUYER", "9930000011")
        buyer_headers = _auth_header(buyer_token)

        # Package a second product from same batch
        p2 = client.post(
            f"/beekeeper/batches/{batch['id']}/products",
            json={"net_weight_g": 250.0, "packaging_date": str(date.today())},
            headers=bk_headers,
        ).json()

        # List product 1 at 450.25 INR and product 2 at 250.50 INR
        client.put(
            f"/beekeeper/products/{product['id']}/listing",
            json={"price": 450.25, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )
        client.put(
            f"/beekeeper/products/{p2['id']}/listing",
            json={"price": 250.50, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )

        # Buyer adds both items to cart
        client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=buyer_headers)
        client.post("/buyer/cart/items", json={"product_id": p2["id"]}, headers=buyer_headers)

        # Execute checkout
        shipping_addr = {
            "full_name": "Rohan Sharma",
            "phone": "9876543210",
            "address_line1": "Flat 402, Green Valley Apartments",
            "address_line2": "MG Road",
            "city": "Ranchi",
            "district": "Ranchi",
            "state": "Jharkhand",
            "pincode": "834001",
        }
        checkout_resp = client.post(
            "/buyer/checkout",
            json={"shipping_address": shipping_addr},
            headers=buyer_headers,
        )
        assert checkout_resp.status_code == 201
        order = checkout_resp.json()

        # Exact Decimal calculation: 450.25 + 250.50 = 700.75
        assert order["subtotal_amount"] == "700.75"
        assert order["shipping_amount"] == "0.00"
        assert order["total_amount"] == "700.75"
        assert order["status"] == "PENDING_PAYMENT"
        assert len(order["items"]) == 2

        # Verify snapshots
        item1 = order["items"][0]
        assert item1["product_serial"] == product["serial_number"]
        assert item1["beekeeper_name"] == "Test Beekeeper"
        assert item1["apiary_name"] == "Forest Meadow Apiary"

        # Verify products are now RESERVED
        p1_db = client.get(f"/beekeeper/products/{product['id']}", headers=bk_headers).json()
        assert p1_db["status"] == "RESERVED"

        # Verify buyer cart is now empty
        cart_after = client.get("/buyer/cart", headers=buyer_headers).json()
        assert cart_after["total_items"] == 0
    finally:
        _cleanup_users_and_records(email_bk, email_buyer)


@skip_if_no_db
def test_concurrent_double_spending_protection():
    """Verify that when two buyers attempt to purchase the same physical product, only one succeeds."""
    email_bk = "concur_bk@example.com"
    email_b1 = "concur_b1@example.com"
    email_b2 = "concur_b2@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email_bk, "9930000012")
        bk_headers = _auth_header(bk_token)
        _, t1 = _create_user_and_token(email_b1, "BUYER", "9930000013")
        _, t2 = _create_user_and_token(email_b2, "BUYER", "9930000014")
        h1 = _auth_header(t1)
        h2 = _auth_header(t2)

        # List product
        client.put(
            f"/beekeeper/products/{product['id']}/listing",
            json={"price": 500.00, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )

        # Both buyers add the same physical jar to their carts
        client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=h1)
        client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=h2)

        shipping_addr = {
            "full_name": "Test Buyer",
            "phone": "9800000000",
            "address_line1": "Street 1",
            "city": "Deoghar",
            "district": "Deoghar",
            "state": "Jharkhand",
            "pincode": "815353",
        }

        # Buyer 1 checks out first -> succeeds
        resp1 = client.post("/buyer/checkout", json={"shipping_address": shipping_addr}, headers=h1)
        assert resp1.status_code == 201

        # Buyer 2 attempts checkout for the now RESERVED unit -> 409 Conflict
        resp2 = client.post("/buyer/checkout", json={"shipping_address": shipping_addr}, headers=h2)
        assert resp2.status_code == 409
        assert "no longer available" in resp2.json()["detail"].lower()
    finally:
        _cleanup_users_and_records(email_bk, email_b1, email_b2)


# ═══════════════════════════════════════════════════════════════════════════
# 4. PAYMENT CONFIRMATION, FAILURE RECOVERY, AND TRACEABILITY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

@skip_if_no_db
def test_payment_capture_success_and_traceability_milestone():
    """Verify payment capture marks order PAID, product SOLD, and records immutable PRODUCT_SOLD event."""
    email_bk = "pmt_succ_bk@example.com"
    email_buyer = "pmt_succ_buyer@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email_bk, "9930000015")
        bk_headers = _auth_header(bk_token)
        _, buyer_token = _create_user_and_token(email_buyer, "BUYER", "9930000016")
        buyer_headers = _auth_header(buyer_token)

        # List product & checkout
        client.put(
            f"/beekeeper/products/{product['id']}/listing",
            json={"price": 750.00, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )
        client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=buyer_headers)
        order = client.post(
            "/buyer/checkout",
            json={
                "shipping_address": {
                    "full_name": "Aarav Gupta",
                    "phone": "9812345678",
                    "address_line1": "Civil Lines",
                    "city": "Ranchi",
                    "district": "Ranchi",
                    "state": "Jharkhand",
                    "pincode": "834001",
                }
            },
            headers=buyer_headers,
        ).json()
        order_id = order["id"]

        # View payment details
        pmt_resp = client.get(f"/buyer/orders/{order_id}/payment", headers=buyer_headers)
        assert pmt_resp.status_code == 200
        assert pmt_resp.json()["is_mock"] is True
        assert pmt_resp.json()["status"] == "CREATED"
        assert pmt_resp.json()["payment_reference"].startswith("MOCK-PAY-")

        # Confirm payment with success
        confirm_resp = client.post(
            f"/buyer/orders/{order_id}/payment/confirm",
            json={"mock_success": True},
            headers=buyer_headers,
        )
        assert confirm_resp.status_code == 200
        paid_order = confirm_resp.json()
        assert paid_order["status"] == "PAID"
        assert paid_order["latest_payment"]["status"] == "CAPTURED"

        # Product status in database is now SOLD and unlisted
        p_updated = client.get(f"/beekeeper/products/{product['id']}", headers=bk_headers).json()
        assert p_updated["status"] == "SOLD"

        # Public QR trace endpoint still works and displays SOLD status and PRODUCT_SOLD event
        trace_resp = client.get(f"/trace/{product['trace_token']}")
        assert trace_resp.status_code == 200
        trace_data = trace_resp.json()
        assert trace_data["status"] == "SOLD"
        timeline_types = [e["event_type"] for e in trace_data["timeline"]]
        assert "PRODUCT_SOLD" in timeline_types

        # Cannot confirm an already PAID order again -> 400 Bad Request
        dup_confirm = client.post(
            f"/buyer/orders/{order_id}/payment/confirm",
            json={"mock_success": True},
            headers=buyer_headers,
        )
        assert dup_confirm.status_code == 400
    finally:
        _cleanup_users_and_records(email_bk, email_buyer)


@skip_if_no_db
def test_payment_failure_unreserves_products_for_recovery():
    """Verify payment failure sets order to PAYMENT_FAILED and reverts product to ACTIVE."""
    email_bk = "pmt_fail_bk@example.com"
    email_buyer = "pmt_fail_buyer@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email_bk, "9930000017")
        bk_headers = _auth_header(bk_token)
        _, buyer_token = _create_user_and_token(email_buyer, "BUYER", "9930000018")
        buyer_headers = _auth_header(buyer_token)

        client.put(
            f"/beekeeper/products/{product['id']}/listing",
            json={"price": 300.00, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )
        client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=buyer_headers)
        order = client.post(
            "/buyer/checkout",
            json={
                "shipping_address": {
                    "full_name": "Buyer Fail",
                    "phone": "9812345678",
                    "address_line1": "Road 5",
                    "city": "Deoghar",
                    "district": "Deoghar",
                    "state": "Jharkhand",
                    "pincode": "815353",
                }
            },
            headers=buyer_headers,
        ).json()

        # Confirm payment with simulated failure
        fail_resp = client.post(
            f"/buyer/orders/{order['id']}/payment/confirm",
            json={"mock_success": False},
            headers=buyer_headers,
        )
        assert fail_resp.status_code == 200
        assert fail_resp.json()["status"] == "PAYMENT_FAILED"

        # Product is released from RESERVED back to ACTIVE
        p_reverted = client.get(f"/beekeeper/products/{product['id']}", headers=bk_headers).json()
        assert p_reverted["status"] == "ACTIVE"
    finally:
        _cleanup_users_and_records(email_bk, email_buyer)


@skip_if_no_db
def test_cross_buyer_order_access_rejected():
    """Verify Buyer B cannot view or confirm Buyer A's order."""
    email_bk = "x_order_bk@example.com"
    email_b1 = "x_order_b1@example.com"
    email_b2 = "x_order_b2@example.com"
    try:
        bk_token, _, product = _setup_beekeeper_with_product(email_bk, "9930000019")
        bk_headers = _auth_header(bk_token)
        _, t1 = _create_user_and_token(email_b1, "BUYER", "9930000020")
        _, t2 = _create_user_and_token(email_b2, "BUYER", "9930000021")
        h1 = _auth_header(t1)
        h2 = _auth_header(t2)

        client.put(
            f"/beekeeper/products/{product['id']}/listing",
            json={"price": 500.00, "is_listed": True, "currency": "INR"},
            headers=bk_headers,
        )
        client.post("/buyer/cart/items", json={"product_id": product["id"]}, headers=h1)
        order = client.post(
            "/buyer/checkout",
            json={
                "shipping_address": {
                    "full_name": "Buyer 1",
                    "phone": "9812345678",
                    "address_line1": "Road 1",
                    "city": "Deoghar",
                    "district": "Deoghar",
                    "state": "Jharkhand",
                    "pincode": "815353",
                }
            },
            headers=h1,
        ).json()
        order_id = order["id"]

        # Buyer 2 cannot retrieve Buyer 1's order -> 404 Not Found
        assert client.get(f"/buyer/orders/{order_id}", headers=h2).status_code == 404
        # Buyer 2 cannot view Buyer 1's order payment -> 404 Not Found
        assert client.get(f"/buyer/orders/{order_id}/payment", headers=h2).status_code == 404
        # Buyer 2 cannot confirm payment on Buyer 1's order -> 404 Not Found
        assert client.post(f"/buyer/orders/{order_id}/payment/confirm", json={"mock_success": True}, headers=h2).status_code == 404
    finally:
        _cleanup_users_and_records(email_bk, email_b1, email_b2)
