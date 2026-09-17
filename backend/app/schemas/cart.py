"""
Pydantic schemas for buyer shopping cart operations.
"""

from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    """Payload to add a specific physical HoneyProduct unit to cart."""

    product_id: int = Field(..., gt=0, description="Database ID of the HoneyProduct unit")


class CartItemResponse(BaseModel):
    """Item in a buyer's cart with live availability status."""

    id: int
    product_id: int
    serial_number: str
    honey_type: str
    net_weight_g: float
    price: Decimal
    currency: str
    is_available: bool
    added_at: datetime

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    """Buyer active cart representation."""

    id: int
    buyer_id: int
    items: List[CartItemResponse]
    subtotal_amount: Decimal
    currency: str
    total_items: int

    model_config = {"from_attributes": True}
