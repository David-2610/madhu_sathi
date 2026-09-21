"""
Public marketplace endpoints for browsing available honey products.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.crud.honey_product import get_product_by_id, list_marketplace_products
from app.db import get_db
from app.models.honey_product import ProductStatus
from app.schemas.marketplace import MarketplaceProductDetail, MarketplaceProductSummary
from app.services.qr import build_trace_url

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])
settings = get_settings()


@router.get(
    "/products",
    response_model=List[MarketplaceProductSummary],
    summary="Browse available marketplace honey products",
)
def get_marketplace_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    honey_type: Optional[str] = Query(None, description="Filter by botanical honey type"),
    db: Session = Depends(get_db),
) -> List[MarketplaceProductSummary]:
    """
    List all active, listed products available for purchase on the marketplace.

    Buyers only see products that are genuinely available for sale.
    """
    products = list_marketplace_products(db, skip=skip, limit=limit, honey_type=honey_type)
    out: List[MarketplaceProductSummary] = []
    for p in products:
        batch = p.batch
        harvest = batch.harvest
        hive = harvest.hive
        apiary = hive.apiary
        beekeeper = apiary.beekeeper

        out.append(
            MarketplaceProductSummary(
                id=p.id,
                serial_number=p.serial_number,
                honey_type=batch.honey_type,
                net_weight_g=p.net_weight_g,
                packaging_date=p.packaging_date,
                price=p.price,
                currency=p.currency,
                is_available=(p.is_listed and p.status == ProductStatus.ACTIVE),
                batch_code=batch.batch_code,
                apiary_name=apiary.name,
                district=beekeeper.district or apiary.location_name,
                state=beekeeper.state,
                beekeeper_code=beekeeper.beekeeper_code,
            )
        )
    return out


@router.get(
    "/products/{product_id}",
    response_model=MarketplaceProductDetail,
    summary="Get detailed view of an available marketplace product",
)
def get_marketplace_product_detail(
    product_id: int,
    db: Session = Depends(get_db),
) -> MarketplaceProductDetail:
    """
    Retrieve product details for an individual listed item.

    Returns HTTP 404 if product is not listed or not currently active.
    """
    p = get_product_by_id(db, product_id)
    if p is None or not p.is_listed or p.status != ProductStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not available for sale in the marketplace.",
        )

    batch = p.batch
    harvest = batch.harvest
    hive = harvest.hive
    apiary = hive.apiary
    beekeeper = apiary.beekeeper

    trace_url = build_trace_url(settings.BASE_URL, p.trace_token)

    return MarketplaceProductDetail(
        id=p.id,
        serial_number=p.serial_number,
        honey_type=batch.honey_type,
        net_weight_g=p.net_weight_g,
        packaging_date=p.packaging_date,
        price=p.price,
        currency=p.currency,
        is_available=True,
        batch_code=batch.batch_code,
        apiary_name=apiary.name,
        district=beekeeper.district or apiary.location_name,
        state=beekeeper.state,
        beekeeper_code=beekeeper.beekeeper_code,
        trace_url=trace_url,
        batch_date=batch.batch_date,
        harvest_date=harvest.harvest_date,
        expiry_date=p.expiry_date,
    )
