"""
Pydantic schemas for Apiary data.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApiaryCreate(BaseModel):
    """Payload for creating a new apiary."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name or title of the apiary",
        examples=["Mustard Farm North Apiary"],
    )
    location_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Descriptive location name",
        examples=["Sector 4, Bharatpur"],
    )
    latitude: Optional[float] = Field(
        None,
        ge=-90.0,
        le=90.0,
        description="GPS Latitude (-90.0 to 90.0)",
        examples=[27.2152],
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180.0,
        le=180.0,
        description="GPS Longitude (-180.0 to 180.0)",
        examples=[77.4930],
    )
    address: Optional[str] = Field(None, max_length=500)


class ApiaryUpdate(BaseModel):
    """Payload for updating an apiary."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location_name: Optional[str] = Field(None, max_length=150)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    address: Optional[str] = Field(None, max_length=500)


class ApiaryResponse(BaseModel):
    """Response representation of an apiary."""

    id: int
    beekeeper_id: int
    name: str
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
