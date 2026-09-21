"""
Pydantic schemas for Honey Chain marketplace products and beekeeper listing management.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceListingUpdate(BaseModel):
    """Payload for beekeepers to set price and marketplace listing visibility."""

    price: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Sale price in specified currency (e.g. 499.00)",
        examples=[Decimal("499.00")],
    )
    is_listed: bool = Field(
        ...,
        description="Whether product is listed and available for sale in the marketplace",
    )
    currency: str = Field(
        "INR",
        min_length=3,
        max_length=3,
        description="Three-letter ISO currency code",
    )


class MarketplaceListingResponse(BaseModel):
    """Beekeeper view of their product listing details."""

    product_id: int
    serial_number: str
    price: Optional[Decimal] = None
    currency: str
    is_listed: bool
    status: str
    is_available_for_sale: bool

    model_config = {"from_attributes": True}


class MarketplaceProductSummary(BaseModel):
    """Consumer/Buyer view of an available marketplace honey product unit."""

    id: int
    serial_number: str
    honey_type: str
    net_weight_g: float
    packaging_date: date
    price: Decimal
    currency: str
    is_available: bool

    batch_code: str
    apiary_name: str
    district: Optional[str] = None
    state: Optional[str] = None
    beekeeper_code: str

    model_config = {"from_attributes": True}


class MarketplaceProductDetail(MarketplaceProductSummary):
    """Detailed consumer view of a marketplace product unit."""

    trace_url: Optional[str] = None
    batch_date: date
    harvest_date: date
    expiry_date: Optional[date] = None
