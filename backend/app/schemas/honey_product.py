"""
Pydantic schemas for Honey Product units.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.honey_product import ProductStatus


class HoneyProductCreate(BaseModel):
    """Payload for packaging and creating an individual honey product unit."""

    net_weight_g: float = Field(
        ...,
        gt=0.0,
        description="Net package weight in grams (e.g., 250, 500, 1000)",
        examples=[500.0],
    )
    packaging_date: date = Field(
        ...,
        description="Date the product was packaged and sealed",
    )
    expiry_date: Optional[date] = Field(
        None,
        description="Best before / expiration date",
    )
    serial_number: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Optional custom serial identifier. Auto-generated if omitted.",
        examples=["HC-PRD-2026-0001"],
    )


class HoneyProductUpdateStatus(BaseModel):
    """Payload for updating product lifecycle status."""

    status: ProductStatus = Field(
        ...,
        description="Updated lifecycle status (ACTIVE, SOLD, REVOKED, SUSPICIOUS)",
    )


class HoneyProductResponse(BaseModel):
    """Beekeeper / internal representation of a packaged honey product."""

    id: int
    batch_id: int
    serial_number: str
    trace_token: str
    net_weight_g: float
    packaging_date: date
    expiry_date: Optional[date] = None
    status: ProductStatus
    trace_url: Optional[str] = None
    qr_code_svg: Optional[str] = None
    # Commerce / marketplace fields
    price: Optional[float] = None
    currency: str = "INR"
    is_listed: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

