"""
Pydantic schemas for Hive data.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.hive import HiveStatus


class HiveCreate(BaseModel):
    """Payload for registering a new hive in an apiary."""

    hive_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique hive identifier within this apiary",
        examples=["HIVE-01"],
    )
    hive_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type/model of the beehive",
        examples=["Langstroth 10-frame"],
    )
    installation_date: Optional[date] = Field(
        None,
        description="Date when the hive was placed/installed",
    )
    status: HiveStatus = Field(
        default=HiveStatus.ACTIVE,
        description="Operational status of the hive",
    )


class HiveUpdate(BaseModel):
    """Payload for updating an existing hive."""

    hive_code: Optional[str] = Field(None, min_length=1, max_length=50)
    hive_type: Optional[str] = Field(None, min_length=1, max_length=50)
    installation_date: Optional[date] = None
    status: Optional[HiveStatus] = None


class HiveResponse(BaseModel):
    """Response representation of a hive."""

    id: int
    apiary_id: int
    hive_code: str
    hive_type: str
    installation_date: Optional[date] = None
    status: HiveStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
