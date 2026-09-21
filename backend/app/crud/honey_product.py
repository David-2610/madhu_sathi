"""
Honey Product CRUD operations.
"""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.honey_batch import HoneyBatch
from app.models.honey_product import HoneyProduct, ProductStatus
from app.schemas.honey_product import HoneyProductCreate



def get_allocated_product_quantity_kg(
    db: Session,
    batch_id: int,
    exclude_product_id: Optional[int] = None,
) -> float:
    """Calculate the total net weight in kilograms already packaged into products for *batch_id*."""
    query = db.query(func.coalesce(func.sum(HoneyProduct.net_weight_g), 0.0)).filter(
        HoneyProduct.batch_id == batch_id
    )
    if exclude_product_id is not None:
        query = query.filter(HoneyProduct.id != exclude_product_id)
    total_grams = query.scalar() or 0.0
    return float(total_grams) / 1000.0


def get_product_by_id(db: Session, product_id: int) -> Optional[HoneyProduct]:
    """Return the HoneyProduct with *product_id*, or None."""
    return db.get(HoneyProduct, product_id)


def get_product_by_token(db: Session, trace_token: str) -> Optional[HoneyProduct]:
    """Return the HoneyProduct with *trace_token*, or None."""
    return db.query(HoneyProduct).filter(HoneyProduct.trace_token == trace_token).first()


def get_product_by_serial(db: Session, serial_number: str) -> Optional[HoneyProduct]:
    """Return the HoneyProduct with *serial_number*, or None."""
    return db.query(HoneyProduct).filter(HoneyProduct.serial_number == serial_number).first()


def list_products_by_batch(db: Session, batch_id: int, skip: int = 0, limit: int = 100) -> List[HoneyProduct]:
    """Return all products packaged from *batch_id*."""
    return (
        db.query(HoneyProduct)
        .filter(HoneyProduct.batch_id == batch_id)
        .order_by(HoneyProduct.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_products_by_beekeeper(db: Session, beekeeper_id: int, skip: int = 0, limit: int = 100) -> List[HoneyProduct]:
    """Return all products belonging to batches owned by *beekeeper_id*."""
    return (
        db.query(HoneyProduct)
        .join(HoneyBatch, HoneyProduct.batch_id == HoneyBatch.id)
        .filter(HoneyBatch.beekeeper_id == beekeeper_id)
        .order_by(HoneyProduct.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_honey_product(
    db: Session,
    batch_id: int,
    payload: HoneyProductCreate,
    trace_token: str,
    serial_number: str,
    qr_svg: Optional[str] = None,
) -> HoneyProduct:
    """Create and persist a new packaged HoneyProduct."""
    product = HoneyProduct(
        batch_id=batch_id,
        serial_number=serial_number,
        trace_token=trace_token,
        net_weight_g=payload.net_weight_g,
        packaging_date=payload.packaging_date,
        expiry_date=payload.expiry_date,
        status=ProductStatus.ACTIVE,
        qr_code_svg=qr_svg,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product_status(
    db: Session,
    product: HoneyProduct,
    new_status: ProductStatus,
) -> HoneyProduct:
    """Update status of *product* (e.g. ACTIVE -> SOLD or REVOKED)."""
    product.status = new_status
    db.commit()
    db.refresh(product)
    return product


def update_product_listing(
    db: Session,
    product: HoneyProduct,
    price: Decimal,
    is_listed: bool,
    currency: str = "INR",
) -> HoneyProduct:
    """Update price and marketplace listing state of *product*."""
    product.price = price
    product.is_listed = is_listed
    product.currency = currency
    db.commit()
    db.refresh(product)
    return product


def list_marketplace_products(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    honey_type: Optional[str] = None,
) -> List[HoneyProduct]:
    """
    Return all products currently listed and available for purchase.

    Only products with is_listed=True and status=ACTIVE are returned.
    """
    query = (
        db.query(HoneyProduct)
        .join(HoneyBatch, HoneyProduct.batch_id == HoneyBatch.id)
        .filter(
            HoneyProduct.is_listed == True,  # noqa: E712
            HoneyProduct.status == ProductStatus.ACTIVE,
        )
    )
    if honey_type:
        query = query.filter(HoneyBatch.honey_type.ilike(f"%{honey_type}%"))

    return query.order_by(HoneyProduct.created_at.desc()).offset(skip).limit(limit).all()

