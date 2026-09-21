"""
Hive CRUD operations.
"""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.hive import Hive
from app.models.honey_harvest import HoneyHarvest
from app.schemas.hive import HiveCreate, HiveUpdate


def get_hive_by_id(db: Session, hive_id: int) -> Optional[Hive]:
    """Return the Hive with the given *hive_id*, or None."""
    return db.get(Hive, hive_id)


def get_hive_by_code_in_apiary(db: Session, apiary_id: int, hive_code: str) -> Optional[Hive]:
    """Return the Hive with *hive_code* in *apiary_id*, or None."""
    return (
        db.query(Hive)
        .filter(Hive.apiary_id == apiary_id, Hive.hive_code == hive_code)
        .first()
    )


def list_hives_by_apiary(db: Session, apiary_id: int, skip: int = 0, limit: int = 100) -> List[Hive]:
    """Return all hives in *apiary_id*."""
    return (
        db.query(Hive)
        .filter(Hive.apiary_id == apiary_id)
        .order_by(Hive.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_hive(db: Session, apiary_id: int, payload: HiveCreate) -> Hive:
    """Create and persist a new Hive in *apiary_id*."""
    hive = Hive(
        apiary_id=apiary_id,
        hive_code=payload.hive_code,
        hive_type=payload.hive_type,
        installation_date=payload.installation_date,
        status=payload.status,
    )
    db.add(hive)
    db.commit()
    db.refresh(hive)

    # Automatically create initial IoT state for the new hive
    from app.models.iot_hive_state import IoTHiveState
    iot_state = IoTHiveState(hive_id=hive.id)
    db.add(iot_state)
    db.commit()

    return hive


def update_hive(db: Session, hive: Hive, payload: HiveUpdate) -> Hive:
    """Update non-null fields on *hive* and persist changes."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hive, field, value)

    db.commit()
    db.refresh(hive)
    return hive


def delete_hive(db: Session, hive: Hive) -> None:
    """Delete *hive* from database."""
    db.delete(hive)
    db.commit()


def count_harvests_for_hive(db: Session, hive_id: int) -> int:
    """Return the count of harvests recorded from *hive_id*."""
    return (
        db.query(func.count(HoneyHarvest.id))
        .filter(HoneyHarvest.hive_id == hive_id)
        .scalar()
        or 0
    )
