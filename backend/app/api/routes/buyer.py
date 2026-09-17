"""
Buyer shopping cart, checkout, order, and payment endpoints.

Accessible exclusively to authenticated users with role BUYER.
"""

from decimal import Decimal
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.crud.cart import (
    add_item_to_cart,
    clear_cart,
    get_cart_item_by_product,
    get_or_create_buyer_cart,
    remove_item_from_cart,
)
from app.crud.honey_product import get_product_by_id
from app.crud.order import (
    CartEmptyError,
    InvalidOrderStateError,
    ProductUnavailableError,
    confirm_order_payment,
    create_order_from_cart,
    get_order_by_id,
    list_orders_by_buyer,
)
from app.db import get_db
from app.models.cart import Cart
from app.models.honey_product import ProductStatus
from app.models.order import Order
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartItemResponse, CartResponse
from app.schemas.common import ErrorResponse
from app.schemas.order import (
    CheckoutRequest,
    OrderItemResponse,
    OrderResponse,
    PaymentConfirmRequest,
    PaymentSummaryResponse,
    ShippingAddress,
)
from app.schemas.user import UserRole

router = APIRouter(prefix="/buyer", tags=["Buyer"])


def _serialize_cart(cart: Cart) -> CartResponse:
    """Build CartResponse with dynamic availability check and Decimal subtotal calculation."""
    items_out = []
    subtotal = Decimal("0.00")
    for item in cart.items:
        p = item.product
        is_avail = bool(p.is_listed and p.status == ProductStatus.ACTIVE and p.price and p.price > Decimal("0.00"))
        item_price = p.price if p.price is not None else Decimal("0.00")
        if is_avail:
            subtotal += item_price

        items_out.append(
            CartItemResponse(
                id=item.id,
                product_id=p.id,
                serial_number=p.serial_number,
                honey_type=p.batch.honey_type,
                net_weight_g=p.net_weight_g,
                price=item_price,
                currency=p.currency,
                is_available=is_avail,
                added_at=item.added_at,
            )
        )

    return CartResponse(
        id=cart.id,
        buyer_id=cart.buyer_id,
        items=items_out,
        subtotal_amount=subtotal,
        currency="INR",
        total_items=len(items_out),
    )


def _serialize_order(order: Order) -> OrderResponse:
    """Build OrderResponse with snapshots and latest payment status."""
    addr_dict = json.loads(order.shipping_address_json)
    items_out = [OrderItemResponse.model_validate(item) for item in order.items]
    latest_pmt = None
    if order.payments:
        sorted_pmts = sorted(order.payments, key=lambda x: x.created_at, reverse=True)
        latest_pmt = PaymentSummaryResponse.model_validate(sorted_pmts[0])

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        buyer_id=order.buyer_id,
        status=order.status,
        subtotal_amount=order.subtotal_amount,
        shipping_amount=order.shipping_amount,
        total_amount=order.total_amount,
        currency=order.currency,
        shipping_address=ShippingAddress(**addr_dict),
        created_at=order.created_at,
        items=items_out,
        latest_payment=latest_pmt,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. CART ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/cart",
    response_model=CartResponse,
    summary="Retrieve buyer's active cart",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
    },
)
def get_cart(
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> CartResponse:
    """Retrieve the current buyer's shopping cart with real-time product availability."""
    cart = get_or_create_buyer_cart(db, current_user.id)
    return _serialize_cart(cart)


@router.post(
    "/cart/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an available product to cart",
    responses={
        400: {"model": ErrorResponse, "description": "Product is not available for purchase"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
        404: {"model": ErrorResponse, "description": "Product not found"},
        409: {"model": ErrorResponse, "description": "Product is already in cart"},
    },
)
def add_cart_item(
    payload: CartItemAdd,
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> CartResponse:
    """
    Add an individual packaged HoneyProduct to the buyer's cart.

    - Rejects if product not found (404).
    - Rejects if product is unlisted, revoked, sold, or suspicious (400).
    - Rejects duplicate item in cart (409).
    """
    product = get_product_by_id(db, payload.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    if not product.is_listed or product.status != ProductStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.serial_number}' is not available for purchase.",
        )

    cart = get_or_create_buyer_cart(db, current_user.id)
    if get_cart_item_by_product(db, cart.id, product.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product '{product.serial_number}' is already in your cart.",
        )

    add_item_to_cart(db, cart, product.id)
    db.refresh(cart)
    return _serialize_cart(cart)


@router.delete(
    "/cart/items/{item_id}",
    response_model=CartResponse,
    summary="Remove an item from cart",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
        404: {"model": ErrorResponse, "description": "Cart item not found"},
    },
)
def delete_cart_item(
    item_id: int,
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> CartResponse:
    """Remove a specific cart item from the buyer's cart."""
    cart = get_or_create_buyer_cart(db, current_user.id)
    deleted = remove_item_from_cart(db, cart, item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found.",
        )
    db.refresh(cart)
    return _serialize_cart(cart)


@router.delete(
    "/cart",
    response_model=CartResponse,
    summary="Clear all items from cart",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
    },
)
def empty_cart(
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> CartResponse:
    """Empty the buyer's cart."""
    cart = get_or_create_buyer_cart(db, current_user.id)
    clear_cart(db, cart)
    db.refresh(cart)
    return _serialize_cart(cart)


# ═══════════════════════════════════════════════════════════════════════════
# 2. CHECKOUT & ORDER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout cart and place an order",
    responses={
        400: {"model": ErrorResponse, "description": "Cart is empty"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
        409: {"model": ErrorResponse, "description": "Product unavailable or state conflict"},
    },
)
def checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """
    Perform atomic checkout from the buyer's active cart.

    - Locks candidate product rows with SELECT ... FOR UPDATE.
    - Re-validates that all items remain active and listed.
    - Computes totals server-side using Decimal arithmetic.
    - Transitions products to RESERVED status to prevent race conditions.
    - Generates a Payment intent via the PaymentProvider.
    - Empties the cart.
    """
    try:
        order = create_order_from_cart(
            db=db,
            buyer_id=current_user.id,
            shipping_address=payload.shipping_address,
        )
    except CartEmptyError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except ProductUnavailableError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err

    return _serialize_order(order)


@router.get(
    "/orders",
    response_model=List[OrderResponse],
    summary="List buyer's orders",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
    },
)
def list_orders(
    skip: int = Query(0, ge=0, description="Number of orders to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max number of orders to return"),
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> List[OrderResponse]:
    """List all orders placed by the authenticated buyer."""
    orders = list_orders_by_buyer(db, current_user.id, skip=skip, limit=limit)
    return [_serialize_order(o) for o in orders]


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Retrieve order details",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
def get_order(
    order_id: int,
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Retrieve details for a specific order. Rejects cross-buyer access with HTTP 404."""
    order = get_order_by_id(db, order_id)
    if order is None or order.buyer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return _serialize_order(order)


# ═══════════════════════════════════════════════════════════════════════════
# 3. PAYMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/orders/{order_id}/payment",
    response_model=PaymentSummaryResponse,
    summary="Get payment details for an order",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
        404: {"model": ErrorResponse, "description": "Order or payment record not found"},
    },
)
def get_order_payment(
    order_id: int,
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> PaymentSummaryResponse:
    """Retrieve the latest payment record for an order. Rejects cross-buyer access with HTTP 404."""
    order = get_order_by_id(db, order_id)
    if order is None or order.buyer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    if not order.payments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payment record found for this order.",
        )
    sorted_pmts = sorted(order.payments, key=lambda x: x.created_at, reverse=True)
    return PaymentSummaryResponse.model_validate(sorted_pmts[0])


@router.post(
    "/orders/{order_id}/payment/confirm",
    response_model=OrderResponse,
    summary="Confirm or simulate payment for an order",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid order state for payment confirmation"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Buyer role required"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
def confirm_payment(
    order_id: int,
    payload: PaymentConfirmRequest,
    current_user: User = Depends(require_role(UserRole.BUYER)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """
    Simulate or verify payment confirmation.

    - If success: sets Order to PAID, sets Products to SOLD, records PRODUCT_SOLD event.
    - If failure: sets Order to PAYMENT_FAILED, sets Products back to ACTIVE.
    """
    order = get_order_by_id(db, order_id)
    if order is None or order.buyer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    try:
        updated_order = confirm_order_payment(
            db=db,
            order=order,
            mock_success=payload.mock_success,
        )
    except InvalidOrderStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return _serialize_order(updated_order)
