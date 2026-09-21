"""
Pydantic schemas for Traceability Events and Consumer Public Trace responses.

SECURITY & PRIVACY INVARIANTS:
- No beekeeper phone numbers, emails, password hashes, or user_ids are included.
- Only non-sensitive regional origin (apiary name, district, state) is exposed.
- Revoked products clearly flag REVOKED status and display a revocation notice.
- Never label excess production or suspicious scan patterns as adulteration/counterfeit.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.honey_product import ProductStatus
from app.models.traceability_event import TraceEventType


class TraceabilityEventCreate(BaseModel):
    """Payload for manually logging a specific traceability event."""

    event_type: TraceEventType
    description: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = None


class TraceabilityEventResponse(BaseModel):
    """Representation of an individual lifecycle traceability event."""

    id: int
    event_type: TraceEventType
    event_date: datetime
    description: str
    location: Optional[str] = None
    event_hash: str
    blockchain_tx_hash: Optional[str] = None
    is_on_chain: bool
    metadata_payload: Optional[str] = None

    model_config = {"from_attributes": True}


class PublicTimelineEventResponse(BaseModel):
    """
    Public, consumer-facing representation of a lifecycle event.
    Guaranteed free of internal database IDs.
    """

    event_type: TraceEventType
    event_date: datetime
    description: str
    location: Optional[str] = None
    event_hash: str
    blockchain_tx_hash: Optional[str] = None
    is_on_chain: bool
    metadata_payload: Optional[str] = None

    model_config = {"from_attributes": True}


class SafeBatchInfo(BaseModel):
    batch_code: str
    batch_date: date


class SafeHarvestInfo(BaseModel):
    harvest_date: date
    honey_type: str


class SafeOriginInfo(BaseModel):
    apiary_name: str
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None


class SafeBeekeeperInfo(BaseModel):
    beekeeper_code: str
    experience_years: Optional[int] = None


class BlockchainVerificationInfo(BaseModel):
    is_on_chain: bool
    network: str
    latest_event_hash: str
    verification_status: str


class PublicTraceResponse(BaseModel):
    """
    Public, unauthenticated consumer trace view.

    Contains exclusively safe traceability data. Guaranteed free of PII and internal database IDs.
    """

    serial_number: str
    status: ProductStatus
    is_valid: bool
    revocation_notice: Optional[str] = None

    honey_type: str
    net_weight_g: float
    packaging_date: date
    expiry_date: Optional[date] = None

    batch: SafeBatchInfo
    harvest: SafeHarvestInfo
    origin: SafeOriginInfo
    beekeeper: SafeBeekeeperInfo

    timeline: List[PublicTimelineEventResponse]
    blockchain_verification: BlockchainVerificationInfo
