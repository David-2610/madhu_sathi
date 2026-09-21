"""
Developer-only routes for system reset and testing.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.crud.beekeeper import create_beekeeper_profile
from app.crud.user import create_user
from app.db import Base, engine, get_db
from app.schemas.beekeeper import BeekeeperProfileCreate
from app.schemas.user import UserCreate, UserRole

router = APIRouter(prefix="/dev", tags=["Developer Tools"])


@router.post(
    "/reset-system",
    status_code=status.HTTP_200_OK,
    summary="[DEV] Reset the entire system and seed test users",
)
def reset_system(
    x_dev_key: str = Header(..., description="Developer secret key for resetting the system"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Drop and recreate all database tables, then seed the 3 test users.
    
    WARNING: THIS IS A DESTRUCTIVE OPERATION.
    It clears all hives, apiaries, telemetries, users, and orders.
    """
    settings = get_settings()

    if settings.APP_ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System reset is only available in development environment.",
        )

    if x_dev_key != "madhu_reset_123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid developer key.",
        )

    # 1. Drop and Recreate All Tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Seed Test Users
    # KVIC Admin
    create_user(db, UserCreate(
        email="kvic_admin@test.com",
        password="123456",
        full_name="Test KVIC Admin",
        role=UserRole.KVIC_ADMIN
    ))

    # Beekeeper
    beekeeper = create_user(db, UserCreate(
        email="beekeeper@test.com",
        password="123456",
        full_name="Test Beekeeper",
        role=UserRole.BEEKEEPER
    ))

    # Buyer
    create_user(db, UserCreate(
        email="buyer@test.com",
        password="123456",
        full_name="Test Buyer",
        role=UserRole.BUYER
    ))

    # 3. Initialize Beekeeper Profile
    create_beekeeper_profile(db, beekeeper.id, BeekeeperProfileCreate(
        beekeeper_code="BEE-TEST-001",
        contact_number="+1-555-0100",
        address="123 Test Apiary Lane",
        experience_years=5
    ))

    return {
        "message": "System Reset Successful",
        "users": [
            {"email": "kvic_admin@test.com", "password": "123456", "role": "KVIC_ADMIN"},
            {"email": "beekeeper@test.com", "password": "123456", "role": "BEEKEEPER (Profile Initialized)"},
            {"email": "buyer@test.com", "password": "123456", "role": "BUYER"},
        ]
    }
