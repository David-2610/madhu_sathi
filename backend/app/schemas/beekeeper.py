"""
Pydantic schemas for Beekeeper Profile data.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BeekeeperProfileCreate(BaseModel):
    """Payload for creating a beekeeper profile."""

    beekeeper_code: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="Unique beekeeper code. Auto-generated if omitted.",
        examples=["BK-UP-2026-001"],
    )
    address: Optional[str] = Field(None, max_length=500)
    village: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    experience_years: Optional[int] = Field(None, ge=0, description="Years of beekeeping experience (>= 0)")


class BeekeeperProfileUpdate(BaseModel):
    """Payload for updating an existing beekeeper profile."""

    address: Optional[str] = Field(None, max_length=500)
    village: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    experience_years: Optional[int] = Field(None, ge=0)


class BeekeeperProfileResponse(BaseModel):
    """Response representation of a beekeeper profile."""

    id: int
    user_id: int
    beekeeper_code: str
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    experience_years: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
