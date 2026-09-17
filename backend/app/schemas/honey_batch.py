"""
Pydantic schemas for Honey Batch data.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.honey_batch import BatchStatus


class HoneyBatchCreate(BaseModel):
    """Payload for creating a processed honey batch from a harvest."""

    batch_code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique batch code / traceability identifier",
        examples=["BATCH-2026-MUSTARD-001"],
    )
    batch_date: date = Field(
        ...,
        description="Date the batch was processed or created",
    )
    quantity_kg: float = Field(
        ...,
        ge=0.0,
        description="Batch quantity in kg (must not exceed available harvest quantity)",
        examples=[10.0],
    )
    honey_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Floral or processed type of honey",
        examples=["Mustard", "Raw Mustard"],
    )
    status: BatchStatus = Field(
        default=BatchStatus.CREATED,
        description="Initial lifecycle status of the batch",
    )


class HoneyBatchUpdate(BaseModel):
    """Payload for updating a honey batch (e.g., status transition or quantity adjustment)."""

    batch_code: Optional[str] = Field(None, min_length=1, max_length=100)
    batch_date: Optional[date] = None
    quantity_kg: Optional[float] = Field(None, ge=0.0)
    honey_type: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[BatchStatus] = None


class HoneyBatchResponse(BaseModel):
    """Response representation of a honey batch."""

    id: int
    batch_code: str
    beekeeper_id: int
    harvest_id: int
    batch_date: date
    quantity_kg: float
    honey_type: str
    status: BatchStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
