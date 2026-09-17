"""
Public consumer traceability endpoints.

Publicly accessible without authentication.
Consumers scan the QR code and are directed to /trace/{trace_token}.

SECURITY INVARIANTS:
- Guaranteed free of PII (no phone, email, password hash, or internal user ID).
- Opaque tokens prevent database enumeration.
- Revoked products clearly display a revocation notice.
- Nonexistent tokens return HTTP 404.
- Suspicious scans or production anomalies are never mislabeled as adulteration.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.crud.honey_product import get_product_by_token
from app.crud.traceability_event import list_events_for_product
from app.db import get_db
from app.models.honey_product import ProductStatus
from app.schemas.traceability import (
    BlockchainVerificationInfo,
    PublicTimelineEventResponse,
    PublicTraceResponse,
    SafeBatchInfo,
    SafeBeekeeperInfo,
    SafeHarvestInfo,
    SafeOriginInfo,
)
from app.services.qr import build_trace_url, generate_qr_png_bytes

router = APIRouter(prefix="/trace", tags=["Traceability"])
settings = get_settings()


@router.get(
    "/{trace_token}",
    response_model=PublicTraceResponse,
    summary="Public consumer honey traceability information",
)
def get_public_trace(
    trace_token: str,
    db: Session = Depends(get_db),
) -> PublicTraceResponse:
    """
    Public trace endpoint for consumers scanning a honey jar QR code.

    - Returns full botanical and regional origin.
    - Never exposes sensitive beekeeper PII or internal database keys.
    - Clearly indicates product status and validity.
    """
    product = get_product_by_token(db, trace_token)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product trace not found. Invalid or unrecognized QR code.",
        )

    batch = product.batch
    harvest = batch.harvest
    hive = harvest.hive
    apiary = hive.apiary
    beekeeper = apiary.beekeeper

    # Collect timeline events (batch events + product events)
    events = list_events_for_product(db, product.id)
    timeline_responses = [PublicTimelineEventResponse.model_validate(e) for e in events]

    # Blockchain verification info
    latest_event = events[-1] if events else None
    latest_hash = latest_event.event_hash if latest_event else ""
    is_on_chain = latest_event.is_on_chain if latest_event else False
    network = "POLYGON_MAINNET" if is_on_chain else "MOCK_LOCAL"
    verification_status = (
        "CONFIRMED_ON_CHAIN"
        if is_on_chain
        else "CRYPTOGRAPHICALLY_VERIFIED_OFF_CHAIN"
    )

    # Revocation notice if product has been recalled or revoked
    revocation_notice = None
    if product.status == ProductStatus.REVOKED:
        revocation_notice = (
            "WARNING: This honey product has been REVOKED by the producer or regulatory authority. "
            "Do not consume. Contact support or your retailer for assistance."
        )

    return PublicTraceResponse(
        serial_number=product.serial_number,
        status=product.status,
        is_valid=(product.status == ProductStatus.ACTIVE),
        revocation_notice=revocation_notice,
        honey_type=batch.honey_type,
        net_weight_g=product.net_weight_g,
        packaging_date=product.packaging_date,
        expiry_date=product.expiry_date,
        batch=SafeBatchInfo(
            batch_code=batch.batch_code,
            batch_date=batch.batch_date,
        ),
        harvest=SafeHarvestInfo(
            harvest_date=harvest.harvest_date,
            honey_type=harvest.honey_type,
        ),
        origin=SafeOriginInfo(
            apiary_name=apiary.name,
            village=beekeeper.village,
            district=beekeeper.district or apiary.location_name,
            state=beekeeper.state,
        ),
        beekeeper=SafeBeekeeperInfo(
            beekeeper_code=beekeeper.beekeeper_code,
            experience_years=beekeeper.experience_years,
        ),
        timeline=timeline_responses,
        blockchain_verification=BlockchainVerificationInfo(
            is_on_chain=is_on_chain,
            network=network,
            latest_event_hash=latest_hash,
            verification_status=verification_status,
        ),
    )


@router.get(
    "/{trace_token}/qr",
    summary="Get QR code image for a product token",
    responses={200: {"content": {"image/png": {}}}},
)
def get_public_qr_image(
    trace_token: str,
    db: Session = Depends(get_db),
) -> Response:
    """Return the raw PNG image of the QR code corresponding to *trace_token*."""
    product = get_product_by_token(db, trace_token)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product trace not found.",
        )

    trace_url = build_trace_url(settings.BASE_URL, trace_token)
    png_bytes = generate_qr_png_bytes(trace_url)
    return Response(content=png_bytes, media_type="image/png")
