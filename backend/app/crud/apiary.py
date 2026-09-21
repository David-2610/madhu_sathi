"""
Apiary CRUD operations.
"""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.apiary import Apiary
from app.models.hive import Hive
from app.schemas.apiary import ApiaryCreate, ApiaryUpdate


def get_apiary_by_id(db: Session, apiary_id: int) -> Optional[Apiary]:
    """Return the Apiary with the given *apiary_id*, or None."""
    return db.get(Apiary, apiary_id)


def list_apiaries_by_beekeeper(db: Session, beekeeper_id: int, skip: int = 0, limit: int = 100) -> List[Apiary]:
    """Return all apiaries belonging to *beekeeper_id*."""
    return (
        db.query(Apiary)
        .filter(Apiary.beekeeper_id == beekeeper_id)
        .order_by(Apiary.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_apiary(db: Session, beekeeper_id: int, payload: ApiaryCreate) -> Apiary:
    """Create and persist a new Apiary for *beekeeper_id*."""
    apiary = Apiary(
        beekeeper_id=beekeeper_id,
        name=payload.name,
        location_name=payload.location_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
    )
    db.add(apiary)
    db.commit()
    db.refresh(apiary)
    return apiary


def update_apiary(db: Session, apiary: Apiary, payload: ApiaryUpdate) -> Apiary:
    """Update non-null fields on *apiary* and persist changes."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(apiary, field, value)

    db.commit()
    db.refresh(apiary)
    return apiary


def delete_apiary(db: Session, apiary: Apiary) -> None:
    """Delete *apiary* from database."""
    db.delete(apiary)
    db.commit()


def count_hives_in_apiary(db: Session, apiary_id: int) -> int:
    """Return the count of hives currently assigned to *apiary_id*."""
    return db.query(func.count(Hive.id)).filter(Hive.apiary_id == apiary_id).scalar() or 0
