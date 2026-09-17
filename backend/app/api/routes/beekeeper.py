"""
Beekeeper management endpoints.

Covers:
- Beekeeper Profile (POST, GET, PUT /beekeeper/profile)
- Apiaries (POST, GET, PUT, DELETE /beekeeper/apiaries)
- Hives (POST, GET /beekeeper/apiaries/{apiary_id}/hives; GET, PUT, DELETE /beekeeper/hives/{hive_id})
- Honey Harvests (POST, GET /beekeeper/hives/{hive_id}/harvests; GET /beekeeper/harvests/{harvest_id})
- Honey Batches (POST /beekeeper/harvests/{harvest_id}/batches; GET, PUT /beekeeper/batches)

All endpoints strictly require the BEEKEEPER role.
Cross-beekeeper access is rejected with HTTP 404 to protect privacy and resource isolation.
"""

import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import require_role
from app.schemas.common import ErrorResponse
from app.crud.apiary import (
    count_hives_in_apiary,
    create_apiary,
    delete_apiary,
    get_apiary_by_id,
    list_apiaries_by_beekeeper,
    update_apiary,
)
from app.crud.beekeeper import (
    create_beekeeper_profile,
    get_beekeeper_by_code,
    get_beekeeper_by_user_id,
    update_beekeeper_profile,
)
from app.crud.hive import (
    count_harvests_for_hive,
    create_hive,
    delete_hive,
    get_hive_by_code_in_apiary,
    get_hive_by_id,
    list_hives_by_apiary,
    update_hive,
)
from app.crud.honey_batch import (
    create_batch,
    get_batch_by_code,
    get_batch_by_id,
    list_batches_by_beekeeper,
    update_batch,
)
from app.crud.honey_harvest import (
    create_harvest,
    get_allocated_batch_quantity,
    get_harvest_by_id,
    list_harvests_by_hive,
)
from app.crud.honey_product import (
    create_honey_product,
    get_allocated_product_quantity_kg,
    get_product_by_id,
    get_product_by_serial,
    list_products_by_batch,
    list_products_by_beekeeper,
    update_product_listing,
    update_product_status,
)
from app.crud.traceability_event import record_event
from app.db import get_db
from app.models.beekeeper import BeekeeperProfile
from app.models.honey_product import ProductStatus
from app.models.traceability_event import TraceEventType
from app.models.user import User
from app.schemas.apiary import ApiaryCreate, ApiaryResponse, ApiaryUpdate
from app.schemas.beekeeper import (
    BeekeeperProfileCreate,
    BeekeeperProfileResponse,
    BeekeeperProfileUpdate,
)
from app.schemas.hive import HiveCreate, HiveResponse, HiveUpdate
from app.schemas.honey_batch import (
    HoneyBatchCreate,
    HoneyBatchResponse,
    HoneyBatchUpdate,
)
from app.schemas.honey_harvest import HoneyHarvestCreate, HoneyHarvestResponse
from app.schemas.honey_product import (
    HoneyProductCreate,
    HoneyProductResponse,
    HoneyProductUpdateStatus,
)
from app.schemas.marketplace import (
    MarketplaceListingResponse,
    MarketplaceListingUpdate,
)
from app.schemas.traceability import TraceabilityEventCreate, TraceabilityEventResponse
from app.schemas.user import UserRole
from app.services.qr import build_trace_url, generate_qr_png_bytes, generate_qr_svg

router = APIRouter(prefix="/beekeeper", tags=["Beekeeper"])


# Allowed lifecycle transitions for HoneyProduct units
VALID_PRODUCT_STATUS_TRANSITIONS: dict[ProductStatus, set[ProductStatus]] = {
    ProductStatus.ACTIVE: {
        ProductStatus.RESERVED,   # Locked in checkout
        ProductStatus.SOLD,
        ProductStatus.REVOKED,
        ProductStatus.SUSPICIOUS,
    },
    ProductStatus.RESERVED: {
        ProductStatus.SOLD,       # Payment confirmed
        ProductStatus.ACTIVE,     # Payment failed / order cancelled
        ProductStatus.REVOKED,    # Revoked while reserved
    },
    ProductStatus.SUSPICIOUS: {
        ProductStatus.ACTIVE,     # Cleared after inspection/investigation
        ProductStatus.REVOKED,    # Confirmed issue / revoked
        ProductStatus.SOLD,       # Cleared and sold
    },
    ProductStatus.SOLD: {
        ProductStatus.REVOKED,    # Post-sale safety recall / revocation
        ProductStatus.SUSPICIOUS, # Post-sale anomaly flagged
    },
    ProductStatus.REVOKED: set(), # Irreversible terminal state
}



# ── Beekeeper Profile Dependency ───────────────────────────────────────────
def get_current_beekeeper(
    current_user: User = Depends(require_role(UserRole.BEEKEEPER)),
    db: Session = Depends(get_db),
) -> BeekeeperProfile:
    """
    Ensure the authenticated BEEKEEPER has an initialized profile.

    Used by downstream apiary, hive, harvest, and batch routes.
    """
    profile = get_beekeeper_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Beekeeper profile not found. Please initialize your profile "
                "first at POST /beekeeper/profile."
            ),
        )
    return profile


# ═══════════════════════════════════════════════════════════════════════════
# 1. BEEKEEPER PROFILE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/profile",
    response_model=BeekeeperProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create beekeeper profile",
)
def create_profile(
    payload: BeekeeperProfileCreate,
    current_user: User = Depends(require_role(UserRole.BEEKEEPER)),
    db: Session = Depends(get_db),
) -> BeekeeperProfile:
    """
    Create a beekeeper profile for the authenticated BEEKEEPER.

    - Rejects duplicate profile creation for the same user with HTTP 409.
    - Rejects duplicate beekeeper_code with HTTP 409.
    """
    existing = get_beekeeper_by_user_id(db, current_user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A beekeeper profile already exists for this account.",
        )

    if payload.beekeeper_code:
        code_owner = get_beekeeper_by_code(db, payload.beekeeper_code)
        if code_owner is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Beekeeper code '{payload.beekeeper_code}' is already registered.",
            )

    return create_beekeeper_profile(db, current_user.id, payload)


@router.get(
    "/profile",
    response_model=BeekeeperProfileResponse,
    summary="Retrieve own beekeeper profile",
)
def get_profile(
    current_user: User = Depends(require_role(UserRole.BEEKEEPER)),
    db: Session = Depends(get_db),
) -> BeekeeperProfile:
    """Return the profile of the authenticated beekeeper."""
    profile = get_beekeeper_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beekeeper profile not found. Please create one at POST /beekeeper/profile.",
        )
    return profile


@router.put(
    "/profile",
    response_model=BeekeeperProfileResponse,
    summary="Update own beekeeper profile",
)
def update_profile(
    payload: BeekeeperProfileUpdate,
    current_user: User = Depends(require_role(UserRole.BEEKEEPER)),
    db: Session = Depends(get_db),
) -> BeekeeperProfile:
    """Update contact, address, and experience fields on the beekeeper profile."""
    profile = get_beekeeper_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beekeeper profile not found.",
        )
    return update_beekeeper_profile(db, profile, payload)


# ═══════════════════════════════════════════════════════════════════════════
# 2. APIARY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/apiaries",
    response_model=ApiaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new apiary",
)
def create_new_apiary(
    payload: ApiaryCreate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> ApiaryResponse:
    """Register a new apiary belonging to the authenticated beekeeper."""
    return create_apiary(db, beekeeper.id, payload)


@router.get(
    "/apiaries",
    response_model=List[ApiaryResponse],
    summary="List own apiaries",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Beekeeper role required"},
    },
)
def list_apiaries(
    skip: int = Query(0, ge=0, description="Number of apiaries to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max number of apiaries to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[ApiaryResponse]:
    """List all apiaries belonging to the authenticated beekeeper."""
    return list_apiaries_by_beekeeper(db, beekeeper.id, skip=skip, limit=limit)


@router.get(
    "/apiaries/{apiary_id}",
    response_model=ApiaryResponse,
    summary="Retrieve an apiary",
)
def get_apiary(
    apiary_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> ApiaryResponse:
    """Retrieve apiary details by ID. Rejects cross-beekeeper access with HTTP 404."""
    apiary = get_apiary_by_id(db, apiary_id)
    if apiary is None or apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apiary not found.",
        )
    return apiary


@router.put(
    "/apiaries/{apiary_id}",
    response_model=ApiaryResponse,
    summary="Update an apiary",
)
def update_existing_apiary(
    apiary_id: int,
    payload: ApiaryUpdate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> ApiaryResponse:
    """Update apiary details. Rejects cross-beekeeper access with HTTP 404."""
    apiary = get_apiary_by_id(db, apiary_id)
    if apiary is None or apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apiary not found.",
        )
    return update_apiary(db, apiary, payload)


@router.delete(
    "/apiaries/{apiary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an apiary",
)
def delete_existing_apiary(
    apiary_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an apiary.

    - Rejects cross-beekeeper access with HTTP 404.
    - Prevents deletion if any hives exist in the apiary (HTTP 400).
    """
    apiary = get_apiary_by_id(db, apiary_id)
    if apiary is None or apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apiary not found.",
        )

    if count_hives_in_apiary(db, apiary_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete apiary with existing hives. Remove or reassign hives first.",
        )

    delete_apiary(db, apiary)


# ═══════════════════════════════════════════════════════════════════════════
# 3. HIVE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/apiaries/{apiary_id}/hives",
    response_model=HiveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a hive in an apiary",
)
def create_new_hive(
    apiary_id: int,
    payload: HiveCreate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HiveResponse:
    """Register a new hive inside the specified apiary."""
    apiary = get_apiary_by_id(db, apiary_id)
    if apiary is None or apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apiary not found.",
        )

    if get_hive_by_code_in_apiary(db, apiary_id, payload.hive_code) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Hive with code '{payload.hive_code}' already exists in this apiary.",
        )

    return create_hive(db, apiary_id, payload)


@router.get(
    "/apiaries/{apiary_id}/hives",
    response_model=List[HiveResponse],
    summary="List hives in an apiary",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Beekeeper role required"},
        404: {"model": ErrorResponse, "description": "Apiary not found"},
    },
)
def list_hives(
    apiary_id: int,
    skip: int = Query(0, ge=0, description="Number of hives to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max number of hives to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HiveResponse]:
    """List all hives in an apiary belonging to the authenticated beekeeper."""
    apiary = get_apiary_by_id(db, apiary_id)
    if apiary is None or apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apiary not found.",
        )
    return list_hives_by_apiary(db, apiary_id, skip=skip, limit=limit)


@router.get(
    "/hives/{hive_id}",
    response_model=HiveResponse,
    summary="Retrieve a hive",
)
def get_hive(
    hive_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HiveResponse:
    """Retrieve hive details by ID. Rejects cross-beekeeper access with HTTP 404."""
    hive = get_hive_by_id(db, hive_id)
    if hive is None or hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )
    return hive


@router.put(
    "/hives/{hive_id}",
    response_model=HiveResponse,
    summary="Update a hive",
)
def update_existing_hive(
    hive_id: int,
    payload: HiveUpdate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HiveResponse:
    """Update hive metadata or status. Rejects cross-beekeeper access with HTTP 404."""
    hive = get_hive_by_id(db, hive_id)
    if hive is None or hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )

    if payload.hive_code and payload.hive_code != hive.hive_code:
        duplicate = get_hive_by_code_in_apiary(db, hive.apiary_id, payload.hive_code)
        if duplicate is not None and duplicate.id != hive.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Hive with code '{payload.hive_code}' already exists in this apiary.",
            )

    return update_hive(db, hive, payload)


@router.delete(
    "/hives/{hive_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a hive",
)
def delete_existing_hive(
    hive_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a hive.

    - Rejects cross-beekeeper access with HTTP 404.
    - Prevents deletion if any harvests have been recorded from this hive (HTTP 400).
    """
    hive = get_hive_by_id(db, hive_id)
    if hive is None or hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )

    if count_harvests_for_hive(db, hive_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete hive with recorded harvests. Traceability records must be preserved.",
        )

    delete_hive(db, hive)


# ═══════════════════════════════════════════════════════════════════════════
# 4. HONEY HARVEST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/hives/{hive_id}/harvests",
    response_model=HoneyHarvestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a honey harvest from a hive",
)
def create_new_harvest(
    hive_id: int,
    payload: HoneyHarvestCreate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyHarvestResponse:
    """
    Record a harvest event from a specific hive.

    - Verifies the hive belongs to an apiary owned by the authenticated beekeeper.
    - Non-negative actual and estimated quantities enforced.
    - NOTE: Excess production is NOT labeled as adulteration.
    """
    hive = get_hive_by_id(db, hive_id)
    if hive is None or hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )

    return create_harvest(db, hive_id, payload)


@router.get(
    "/hives/{hive_id}/harvests",
    response_model=List[HoneyHarvestResponse],
    summary="List harvests for a hive",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Beekeeper role required"},
        404: {"model": ErrorResponse, "description": "Hive not found"},
    },
)
def list_harvests(
    hive_id: int,
    skip: int = Query(0, ge=0, description="Number of harvests to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max number of harvests to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HoneyHarvestResponse]:
    """List all harvests recorded from a hive belonging to the authenticated beekeeper."""
    hive = get_hive_by_id(db, hive_id)
    if hive is None or hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hive not found.",
        )
    return list_harvests_by_hive(db, hive_id, skip=skip, limit=limit)


@router.get(
    "/harvests/{harvest_id}",
    response_model=HoneyHarvestResponse,
    summary="Retrieve a harvest",
)
def get_harvest(
    harvest_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyHarvestResponse:
    """Retrieve harvest details by ID. Rejects cross-beekeeper access with HTTP 404."""
    harvest = get_harvest_by_id(db, harvest_id)
    if harvest is None or harvest.hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Harvest not found.",
        )
    return harvest


# ═══════════════════════════════════════════════════════════════════════════
# 5. HONEY BATCH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/harvests/{harvest_id}/batches",
    response_model=HoneyBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a batch from a harvest",
)
def create_new_batch(
    harvest_id: int,
    payload: HoneyBatchCreate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyBatchResponse:
    """
    Create a honey batch from a specific harvest.

    - Harvest must belong to the authenticated beekeeper.
    - Batch code must be unique across the platform.
    - Batch quantity must not exceed available harvest quantity.
    """
    harvest = get_harvest_by_id(db, harvest_id)
    if harvest is None or harvest.hive.apiary.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Harvest not found.",
        )

    if get_batch_by_code(db, payload.batch_code) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Batch code '{payload.batch_code}' already exists.",
        )

    allocated = get_allocated_batch_quantity(db, harvest_id)
    available = harvest.actual_quantity_kg - allocated
    if payload.quantity_kg > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Batch quantity ({payload.quantity_kg} kg) exceeds available "
                f"harvest quantity ({available:.2f} kg remaining of {harvest.actual_quantity_kg} kg total)."
            ),
        )

    return create_batch(db, beekeeper.id, harvest_id, payload)


@router.get(
    "/batches",
    response_model=List[HoneyBatchResponse],
    summary="List own honey batches",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Beekeeper role required"},
    },
)
def list_batches(
    skip: int = Query(0, ge=0, description="Number of batches to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max number of batches to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HoneyBatchResponse]:
    """List all honey batches created by the authenticated beekeeper."""
    return list_batches_by_beekeeper(db, beekeeper.id, skip=skip, limit=limit)


@router.get(
    "/batches/{batch_id}",
    response_model=HoneyBatchResponse,
    summary="Retrieve a honey batch",
)
def get_batch(
    batch_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyBatchResponse:
    """Retrieve honey batch details by ID. Rejects cross-beekeeper access with HTTP 404."""
    batch = get_batch_by_id(db, batch_id)
    if batch is None or batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found.",
        )
    return batch


@router.put(
    "/batches/{batch_id}",
    response_model=HoneyBatchResponse,
    summary="Update a honey batch",
)
def update_existing_batch(
    batch_id: int,
    payload: HoneyBatchUpdate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyBatchResponse:
    """
    Update a honey batch (status or quantity).

    - Rejects cross-beekeeper access with HTTP 404.
    - Verifies adjusted quantity does not exceed available harvest capacity.
    """
    batch = get_batch_by_id(db, batch_id)
    if batch is None or batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found.",
        )

    if payload.batch_code and payload.batch_code != batch.batch_code:
        duplicate = get_batch_by_code(db, payload.batch_code)
        if duplicate is not None and duplicate.id != batch.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Batch code '{payload.batch_code}' already exists.",
            )

    if payload.quantity_kg is not None and payload.quantity_kg != batch.quantity_kg:
        allocated_others = get_allocated_batch_quantity(
            db, batch.harvest_id, exclude_batch_id=batch.id
        )
        available = batch.harvest.actual_quantity_kg - allocated_others
        if payload.quantity_kg > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Updated batch quantity ({payload.quantity_kg} kg) exceeds available "
                    f"harvest quantity ({available:.2f} kg remaining)."
                ),
            )
        packaged_kg = get_allocated_product_quantity_kg(db, batch.id)
        if payload.quantity_kg < packaged_kg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reduce batch quantity to {payload.quantity_kg} kg: "
                    f"{packaged_kg:.3f} kg already packaged into products."
                ),
            )

    return update_batch(db, batch, payload)


# ═══════════════════════════════════════════════════════════════════════════
# 6. HONEY PRODUCT / PACKAGING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/batches/{batch_id}/products",
    response_model=HoneyProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Package an individual honey product from a batch",
)
def package_product(
    batch_id: int,
    payload: HoneyProductCreate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyProductResponse:
    """
    Package an individual bottle/jar from a honey batch.

    - Generates a unique, cryptographically random opaque trace token.
    - Generates a unique serial number if not provided.
    - Automatically builds and embeds a backend-generated QR code vector.
    - Logs initial immutable traceability events with SHA-256 cryptographic proofs.
    """
    batch = get_batch_by_id(db, batch_id)
    if batch is None or batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found.",
        )

    # Invariant: sum(product quantities for a batch) <= batch.quantity_kg
    allocated_kg = get_allocated_product_quantity_kg(db, batch_id)
    product_kg = payload.net_weight_g / 1000.0
    available_kg = batch.quantity_kg - allocated_kg
    if product_kg > available_kg + 1e-6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Product package quantity ({product_kg:.3f} kg) exceeds available "
                f"batch capacity ({max(0.0, available_kg):.3f} kg remaining of {batch.quantity_kg:.2f} kg total)."
            ),
        )

    trace_token = secrets.token_urlsafe(32)

    if payload.serial_number:
        if get_product_by_serial(db, payload.serial_number) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Serial number '{payload.serial_number}' already exists.",
            )
        serial_number = payload.serial_number
    else:
        serial_number = f"HC-PRD-{batch.id:04d}-{secrets.token_hex(4).upper()}"

    settings = get_settings()
    trace_url = build_trace_url(settings.BASE_URL, trace_token)
    qr_svg = generate_qr_svg(trace_url)

    product = create_honey_product(
        db=db,
        batch_id=batch_id,
        payload=payload,
        trace_token=trace_token,
        serial_number=serial_number,
        qr_svg=qr_svg,
    )

    # Initial traceability events
    record_event(
        db=db,
        event_type=TraceEventType.PRODUCT_CREATED,
        description=f"Unit packaged with serial {product.serial_number}",
        entity_code=product.serial_number,
        product_id=product.id,
        batch_id=batch.id,
        metadata={
            "net_weight_g": product.net_weight_g,
            "packaging_date": str(product.packaging_date),
        },
    )
    record_event(
        db=db,
        event_type=TraceEventType.PACKAGED,
        description=f"Packaged from batch {batch.batch_code} ({batch.honey_type})",
        entity_code=product.serial_number,
        product_id=product.id,
        batch_id=batch.id,
        metadata={
            "batch_code": batch.batch_code,
            "honey_type": batch.honey_type,
        },
    )

    resp = HoneyProductResponse.model_validate(product)
    resp.trace_url = trace_url
    return resp


@router.get(
    "/batches/{batch_id}/products",
    response_model=List[HoneyProductResponse],
    summary="List products packaged from a batch",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Beekeeper role required"},
        404: {"model": ErrorResponse, "description": "Batch not found"},
    },
)
def list_batch_products(
    batch_id: int,
    skip: int = Query(0, ge=0, description="Number of products to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max number of products to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HoneyProductResponse]:
    """List all individual product units packaged from *batch_id*."""
    batch = get_batch_by_id(db, batch_id)
    if batch is None or batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found.",
        )
    products = list_products_by_batch(db, batch_id, skip=skip, limit=limit)
    settings = get_settings()
    out = []
    for p in products:
        item = HoneyProductResponse.model_validate(p)
        item.trace_url = build_trace_url(settings.BASE_URL, p.trace_token)
        out.append(item)
    return out


@router.get(
    "/products",
    response_model=List[HoneyProductResponse],
    summary="List all packaged products owned by beekeeper",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Beekeeper role required"},
    },
)
def list_all_products(
    skip: int = Query(0, ge=0, description="Number of products to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max number of products to return"),
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> List[HoneyProductResponse]:
    """List all packaged products owned by the authenticated beekeeper."""
    products = list_products_by_beekeeper(db, beekeeper.id, skip=skip, limit=limit)
    settings = get_settings()
    out = []
    for p in products:
        item = HoneyProductResponse.model_validate(p)
        item.trace_url = build_trace_url(settings.BASE_URL, p.trace_token)
        out.append(item)
    return out


@router.get(
    "/products/{product_id}",
    response_model=HoneyProductResponse,
    summary="Retrieve an individual honey product",
)
def get_product(
    product_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyProductResponse:
    """Retrieve details for a specific product. Rejects cross-beekeeper access with HTTP 404."""
    product = get_product_by_id(db, product_id)
    if product is None or product.batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    settings = get_settings()
    resp = HoneyProductResponse.model_validate(product)
    resp.trace_url = build_trace_url(settings.BASE_URL, product.trace_token)
    return resp


@router.get(
    "/products/{product_id}/qr",
    summary="Get QR code image for a product",
    responses={200: {"content": {"image/png": {}}}},
)
def get_product_qr_image(
    product_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> Response:
    """Return the raw PNG bytes of the product's QR code."""
    product = get_product_by_id(db, product_id)
    if product is None or product.batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    settings = get_settings()
    trace_url = build_trace_url(settings.BASE_URL, product.trace_token)
    png_bytes = generate_qr_png_bytes(trace_url)
    return Response(content=png_bytes, media_type="image/png")


@router.put(
    "/products/{product_id}/status",
    response_model=HoneyProductResponse,
    summary="Update status of an individual honey product",
)
def update_product_status_endpoint(
    product_id: int,
    payload: HoneyProductUpdateStatus,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> HoneyProductResponse:
    """Update status of a packaged unit with strict lifecycle transition policy."""
    product = get_product_by_id(db, product_id)
    if product is None or product.batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    current_status = product.status
    target_status = payload.status

    if target_status != current_status:
        allowed = VALID_PRODUCT_STATUS_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid product status transition from '{current_status.value}' "
                    f"to '{target_status.value}'."
                ),
            )
        product = update_product_status(db, product, target_status)

    settings = get_settings()
    resp = HoneyProductResponse.model_validate(product)
    resp.trace_url = build_trace_url(settings.BASE_URL, product.trace_token)
    return resp


@router.post(
    "/products/{product_id}/events",
    response_model=TraceabilityEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an additional traceability event on a product",
)
def add_product_traceability_event(
    product_id: int,
    payload: TraceabilityEventCreate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> TraceabilityEventResponse:
    """Record an additional lifecycle milestone (e.g. QUALITY_TEST_ADDED, PROCESSING_RECORDED)."""
    product = get_product_by_id(db, product_id)
    if product is None or product.batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    event = record_event(
        db=db,
        event_type=payload.event_type,
        description=payload.description,
        entity_code=product.serial_number,
        product_id=product.id,
        batch_id=product.batch_id,
        location=payload.location,
        metadata=payload.metadata,
    )
    return TraceabilityEventResponse.model_validate(event)


# ═══════════════════════════════════════════════════════════════════════════
# 7. PRODUCT MARKETPLACE LISTING MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@router.put(
    "/products/{product_id}/listing",
    response_model=MarketplaceListingResponse,
    summary="Update marketplace listing and pricing for a product",
)
def update_product_listing_endpoint(
    product_id: int,
    payload: MarketplaceListingUpdate,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> MarketplaceListingResponse:
    """
    Configure pricing and marketplace listing for an individual product.

    - Rejects cross-beekeeper access with HTTP 404.
    - Prevents listing products that are REVOKED, SOLD, or SUSPICIOUS (HTTP 400).
    """
    product = get_product_by_id(db, product_id)
    if product is None or product.batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    if payload.is_listed and product.status != ProductStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot list product with status '{product.status.value}'. "
                f"Only ACTIVE products may be listed for sale."
            ),
        )

    product = update_product_listing(
        db=db,
        product=product,
        price=payload.price,
        is_listed=payload.is_listed,
        currency=payload.currency,
    )

    return MarketplaceListingResponse(
        product_id=product.id,
        serial_number=product.serial_number,
        price=product.price,
        currency=product.currency,
        is_listed=product.is_listed,
        status=product.status.value,
        is_available_for_sale=bool(product.is_listed and product.status == ProductStatus.ACTIVE),
    )


@router.get(
    "/products/{product_id}/listing",
    response_model=MarketplaceListingResponse,
    summary="Retrieve marketplace listing details for a product",
)
def get_product_listing_endpoint(
    product_id: int,
    beekeeper: BeekeeperProfile = Depends(get_current_beekeeper),
    db: Session = Depends(get_db),
) -> MarketplaceListingResponse:
    """Retrieve listing and pricing status for a beekeeper's product."""
    product = get_product_by_id(db, product_id)
    if product is None or product.batch.beekeeper_id != beekeeper.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return MarketplaceListingResponse(
        product_id=product.id,
        serial_number=product.serial_number,
        price=product.price,
        currency=product.currency,
        is_listed=product.is_listed,
        status=product.status.value,
        is_available_for_sale=bool(product.is_listed and product.status == ProductStatus.ACTIVE),
    )


