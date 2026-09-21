"""
Pydantic schemas for Honey Harvest data.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class HoneyHarvestCreate(BaseModel):
    """Payload for recording a honey harvest from a hive."""

    harvest_date: date = Field(
        ...,
        description="Date the honey was harvested",
    )
    estimated_quantity_kg: Optional[float] = Field(
        None,
        ge=0.0,
        description="Estimated quantity in kg (must be non-negative)",
        examples=[12.5],
    )
    actual_quantity_kg: float = Field(
        ...,
        ge=0.0,
        description="Actual measured quantity in kg (must be non-negative)",
        examples=[14.2],
    )
    honey_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Flora / botanical origin of the honey",
        examples=["Mustard", "Multifloral", "Eucalyptus", "Acacia"],
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional observation or field notes",
    )


class HoneyHarvestResponse(BaseModel):
    """Response representation of a honey harvest."""

    id: int
    hive_id: int
    harvest_date: date
    estimated_quantity_kg: Optional[float] = None
    actual_quantity_kg: float
    honey_type: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
