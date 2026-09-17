"""
Honey Harvest CRUD operations.
"""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.honey_batch import BatchStatus, HoneyBatch
from app.models.honey_harvest import HoneyHarvest
from app.schemas.honey_harvest import HoneyHarvestCreate


def get_harvest_by_id(db: Session, harvest_id: int) -> Optional[HoneyHarvest]:
    """Return the HoneyHarvest with the given *harvest_id*, or None."""
    return db.get(HoneyHarvest, harvest_id)


def list_harvests_by_hive(db: Session, hive_id: int, skip: int = 0, limit: int = 100) -> List[HoneyHarvest]:
    """Return all harvests from *hive_id* ordered by date descending."""
    return (
        db.query(HoneyHarvest)
        .filter(HoneyHarvest.hive_id == hive_id)
        .order_by(HoneyHarvest.harvest_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_harvest(
    db: Session,
    hive_id: int,
    payload: HoneyHarvestCreate,
) -> HoneyHarvest:
    """Create and persist a new HoneyHarvest for *hive_id*."""
    harvest = HoneyHarvest(
        hive_id=hive_id,
        harvest_date=payload.harvest_date,
        estimated_quantity_kg=payload.estimated_quantity_kg,
        actual_quantity_kg=payload.actual_quantity_kg,
        honey_type=payload.honey_type,
        notes=payload.notes,
    )
    db.add(harvest)
    db.commit()
    db.refresh(harvest)
    return harvest


def get_allocated_batch_quantity(
    db: Session,
    harvest_id: int,
    exclude_batch_id: Optional[int] = None,
) -> float:
    """
    Calculate the total kg of honey already allocated into active/non-recalled batches.

    Recalled batches do not lock production volume, but all other statuses do.
    """
    query = db.query(func.coalesce(func.sum(HoneyBatch.quantity_kg), 0.0)).filter(
        HoneyBatch.harvest_id == harvest_id,
        HoneyBatch.status != BatchStatus.RECALLED,
    )
    if exclude_batch_id is not None:
        query = query.filter(HoneyBatch.id != exclude_batch_id)

    total = query.scalar()
    return float(total or 0.0)
