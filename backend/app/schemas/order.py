"""
Pydantic schemas for buyer checkout, orders, order items, and payment operations.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus
from app.models.payment import PaymentStatus


class ShippingAddress(BaseModel):
    """Customer shipping delivery address."""

    full_name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=10, max_length=15)
    address_line1: str = Field(..., min_length=3, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=4, max_length=10)


class CheckoutRequest(BaseModel):
    """Payload to initiate checkout from the buyer's active cart."""

    shipping_address: ShippingAddress


class OrderItemResponse(BaseModel):
    """Historical snapshot of an item within an order."""

    id: int
    product_id: int
    product_serial: str
    honey_type: str
    net_weight_g: float
    unit_price: Decimal
    currency: str
    batch_code: str
    beekeeper_code: str
    beekeeper_name: str
    apiary_name: str

    model_config = {"from_attributes": True}


class PaymentSummaryResponse(BaseModel):
    """Payment record summary."""

    id: int
    payment_reference: str
    provider: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    is_mock: bool

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    """Complete customer order representation."""

    id: int
    order_number: str
    buyer_id: int
    status: OrderStatus
    subtotal_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    currency: str
    shipping_address: ShippingAddress
    created_at: datetime
    items: List[OrderItemResponse]
    latest_payment: Optional[PaymentSummaryResponse] = None

    model_config = {"from_attributes": True}


class PaymentConfirmRequest(BaseModel):
    """Payload to confirm or simulate payment completion."""

    mock_success: bool = Field(
        True,
        description="Whether to simulate payment authorization/capture success or failure",
    )
