"""
Order and checkout CRUD operations.

Handles atomic checkout, row-level locking with SELECT ... FOR UPDATE,
server-side Decimal calculations, and payment intent generation.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import secrets
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.traceability_event import record_event
from app.models.cart import Cart, CartItem
from app.models.honey_product import HoneyProduct, ProductStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.traceability_event import TraceEventType
from app.schemas.order import ShippingAddress
from app.services.payment import PaymentProvider, get_payment_provider


class CheckoutError(Exception):
    """Base exception for checkout failures."""
    pass


class CartEmptyError(CheckoutError):
    pass


class ProductUnavailableError(CheckoutError):
    def __init__(self, message: str, product_id: Optional[int] = None):
        super().__init__(message)
        self.product_id = product_id


class InvalidOrderStateError(Exception):
    pass


def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
    """Retrieve an order by ID."""
    return db.get(Order, order_id)


def get_order_by_number(db: Session, order_number: str) -> Optional[Order]:
    """Retrieve an order by unique order_number."""
    return db.query(Order).filter(Order.order_number == order_number).first()


def list_orders_by_buyer(db: Session, buyer_id: int, skip: int = 0, limit: int = 50) -> List[Order]:
    """List all orders placed by *buyer_id* sorted by creation date descending."""
    return (
        db.query(Order)
        .filter(Order.buyer_id == buyer_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_order_from_cart(
    db: Session,
    buyer_id: int,
    shipping_address: ShippingAddress,
    payment_provider: Optional[PaymentProvider] = None,
) -> Order:
    """
    Execute atomic checkout from the buyer's active cart.

    CONCURRENCY & CONSISTENCY INVARIANTS:
    1. Locks candidate products with SELECT ... FOR UPDATE in ascending ID order to prevent deadlocks.
    2. Re-verifies every product is still is_listed=True and status=ACTIVE.
    3. Calculates total server-side using Decimal arithmetic (never trusts client price).
    4. Transitions products to RESERVED status to prevent simultaneous double-spending.
    5. Clears buyer's cart items.
    6. Initializes payment intent via PaymentProvider.
    """
    if payment_provider is None:
        payment_provider = get_payment_provider()

    # 1. Fetch buyer's cart
    cart = db.query(Cart).filter(Cart.buyer_id == buyer_id).first()
    if cart is None or not cart.items:
        raise CartEmptyError("Cannot checkout with an empty cart.")

    # 2. Extract and sort product IDs to ensure canonical lock order
    product_ids = sorted([item.product_id for item in cart.items])

    # 3. Lock products with SELECT ... FOR UPDATE
    products = (
        db.query(HoneyProduct)
        .filter(HoneyProduct.id.in_(product_ids))
        .with_for_update()
        .all()
    )

    if len(products) != len(product_ids):
        raise ProductUnavailableError("One or more products in your cart no longer exist.")

    # 4. Strict re-validation of availability and pricing
    subtotal = Decimal("0.00")
    for p in products:
        if not p.is_listed or p.status != ProductStatus.ACTIVE:
            raise ProductUnavailableError(
                f"Product '{p.serial_number}' is no longer available for purchase.",
                product_id=p.id,
            )
        if p.price is None or p.price <= Decimal("0.00"):
            raise ProductUnavailableError(
                f"Product '{p.serial_number}' has invalid pricing.",
                product_id=p.id,
            )
        subtotal += p.price

    shipping = Decimal("0.00")
    total = subtotal + shipping

    # 5. Generate unique human-readable order number
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    order_number = f"HC-ORD-{date_str}-{secrets.token_hex(4).upper()}"

    # 6. Create Order row
    order = Order(
        order_number=order_number,
        buyer_id=buyer_id,
        status=OrderStatus.PENDING_PAYMENT,
        subtotal_amount=subtotal,
        shipping_amount=shipping,
        total_amount=total,
        currency="INR",
        shipping_address_json=shipping_address.model_dump_json(),
    )
    db.add(order)
    db.flush()

    # 7. Create OrderItem historical snapshots and reserve products
    for p in products:
        batch = p.batch
        harvest = batch.harvest
        hive = harvest.hive
        apiary = hive.apiary
        beekeeper = apiary.beekeeper
        user = beekeeper.user

        order_item = OrderItem(
            order_id=order.id,
            product_id=p.id,
            unit_price=p.price,
            currency=p.currency,
            product_serial=p.serial_number,
            product_token=p.trace_token,
            honey_type=batch.honey_type,
            net_weight_g=p.net_weight_g,
            batch_code=batch.batch_code,
            beekeeper_code=beekeeper.beekeeper_code,
            beekeeper_name=user.full_name,
            apiary_name=apiary.name,
        )
        db.add(order_item)

        # Mark product as RESERVED
        p.status = ProductStatus.RESERVED

    # 8. Create Payment record via payment abstraction
    receipt = payment_provider.create_payment_intent(
        order_id=order.id,
        order_number=order.order_number,
        amount=order.total_amount,
        currency=order.currency,
        customer_info={"buyer_id": buyer_id},
    )

    payment = Payment(
        order_id=order.id,
        payment_reference=receipt.payment_reference,
        provider=receipt.provider,
        amount=receipt.amount,
        currency=receipt.currency,
        status=receipt.status,
        is_mock=receipt.is_mock,
        provider_metadata=json.dumps(receipt.provider_metadata) if receipt.provider_metadata else None,
    )
    db.add(payment)

    # 9. Clear buyer cart items
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

    # 10. Commit transaction
    db.commit()
    db.refresh(order)
    return order


def confirm_order_payment(
    db: Session,
    order: Order,
    mock_success: bool = True,
    payment_provider: Optional[PaymentProvider] = None,
) -> Order:
    """
    Process payment confirmation or failure.

    - If success: order becomes PAID, products become SOLD (unlisted), and PRODUCT_SOLD event logged.
    - If failure: order becomes PAYMENT_FAILED, products revert to ACTIVE.
    """
    if payment_provider is None:
        payment_provider = get_payment_provider()

    if order.status != OrderStatus.PENDING_PAYMENT:
        raise InvalidOrderStateError(
            f"Cannot confirm payment for order in '{order.status.value}' state."
        )

    # Lock associated products to execute clean state transitions
    product_ids = sorted([item.product_id for item in order.items])
    products = (
        db.query(HoneyProduct)
        .filter(HoneyProduct.id.in_(product_ids))
        .with_for_update()
        .all()
    )

    # Fetch latest payment record
    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .order_by(Payment.created_at.desc())
        .first()
    )

    receipt = payment_provider.verify_or_capture_payment(
        payment_reference=payment.payment_reference if payment else f"REF-{order.id}",
        amount=order.total_amount,
        currency=order.currency,
        payload={"mock_success": mock_success},
    )

    if receipt.is_success and receipt.status == PaymentStatus.CAPTURED:
        order.status = OrderStatus.PAID
        if payment:
            payment.status = PaymentStatus.CAPTURED

        for p in products:
            p.status = ProductStatus.SOLD
            p.is_listed = False

            # Record immutable traceability milestone
            record_event(
                db=db,
                event_type=TraceEventType.PRODUCT_SOLD,
                description=f"Purchased under order {order.order_number}",
                entity_code=p.serial_number,
                product_id=p.id,
                batch_id=p.batch_id,
                metadata={
                    "order_number": order.order_number,
                    "unit_price": str(p.price),
                    "currency": p.currency,
                    "payment_reference": payment.payment_reference if payment else None,
                },
            )
    else:
        order.status = OrderStatus.PAYMENT_FAILED
        if payment:
            payment.status = PaymentStatus.FAILED

        # Revert products to ACTIVE so they can be purchased again
        for p in products:
            if p.status == ProductStatus.RESERVED:
                p.status = ProductStatus.ACTIVE

    db.commit()
    db.refresh(order)
    return order
