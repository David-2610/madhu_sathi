"""
Beekeeper Profile CRUD operations.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.beekeeper import BeekeeperProfile
from app.schemas.beekeeper import BeekeeperProfileCreate, BeekeeperProfileUpdate


def get_beekeeper_by_user_id(db: Session, user_id: int) -> Optional[BeekeeperProfile]:
    """Return the BeekeeperProfile associated with *user_id*, or None."""
    return db.query(BeekeeperProfile).filter(BeekeeperProfile.user_id == user_id).first()


def get_beekeeper_by_code(db: Session, code: str) -> Optional[BeekeeperProfile]:
    """Return the BeekeeperProfile with the given *code*, or None."""
    return db.query(BeekeeperProfile).filter(BeekeeperProfile.beekeeper_code == code).first()


def create_beekeeper_profile(
    db: Session,
    user_id: int,
    payload: BeekeeperProfileCreate,
) -> BeekeeperProfile:
    """Create and persist a new BeekeeperProfile for *user_id*."""
    code = payload.beekeeper_code or f"BK-{user_id:04d}"

    profile = BeekeeperProfile(
        user_id=user_id,
        beekeeper_code=code,
        address=payload.address,
        village=payload.village,
        district=payload.district,
        state=payload.state,
        pincode=payload.pincode,
        experience_years=payload.experience_years,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_beekeeper_profile(
    db: Session,
    profile: BeekeeperProfile,
    payload: BeekeeperProfileUpdate,
) -> BeekeeperProfile:
    """Update non-null fields on *profile* and persist changes."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
