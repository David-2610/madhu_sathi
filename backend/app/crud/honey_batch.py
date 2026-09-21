"""
Honey Batch CRUD operations.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.honey_batch import HoneyBatch
from app.schemas.honey_batch import HoneyBatchCreate, HoneyBatchUpdate


def get_batch_by_id(db: Session, batch_id: int) -> Optional[HoneyBatch]:
    """Return the HoneyBatch with the given *batch_id*, or None."""
    return db.get(HoneyBatch, batch_id)


def get_batch_by_code(db: Session, batch_code: str) -> Optional[HoneyBatch]:
    """Return the HoneyBatch with the given *batch_code*, or None."""
    return db.query(HoneyBatch).filter(HoneyBatch.batch_code == batch_code).first()


def list_batches_by_beekeeper(db: Session, beekeeper_id: int, skip: int = 0, limit: int = 100) -> List[HoneyBatch]:
    """Return all honey batches belonging to *beekeeper_id*."""
    return (
        db.query(HoneyBatch)
        .filter(HoneyBatch.beekeeper_id == beekeeper_id)
        .order_by(HoneyBatch.batch_date.desc(), HoneyBatch.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_batch(
    db: Session,
    beekeeper_id: int,
    harvest_id: int,
    payload: HoneyBatchCreate,
) -> HoneyBatch:
    """Create and persist a new HoneyBatch."""
    batch = HoneyBatch(
        batch_code=payload.batch_code,
        beekeeper_id=beekeeper_id,
        harvest_id=harvest_id,
        batch_date=payload.batch_date,
        quantity_kg=payload.quantity_kg,
        honey_type=payload.honey_type,
        status=payload.status,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def update_batch(
    db: Session,
    batch: HoneyBatch,
    payload: HoneyBatchUpdate,
) -> HoneyBatch:
    """Update non-null fields on *batch* and persist changes."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(batch, field, value)

    db.commit()
    db.refresh(batch)
    return batch
