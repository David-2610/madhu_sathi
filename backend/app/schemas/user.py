"""
Pydantic schemas for user-related data.

These schemas control what data enters and leaves the API.

SECURITY INVARIANT: ``password_hash`` is NEVER included in any response
schema. Only ``UserResponse`` (which omits it) is ever returned to clients.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Role enum ──────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    """Supported user roles in Honey Chain."""

    BUYER = "BUYER"
    BEEKEEPER = "BEEKEEPER"
    KVIC_ADMIN = "KVIC_ADMIN"


# ── Request schemas ────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    """Payload for POST /auth/register."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
        examples=["Priya Sharma"],
    )
    email: EmailStr = Field(..., description="Unique email address")
    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Mobile number (10–15 digits)",
        examples=["9876543210"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 characters)",
    )
    role: UserRole = Field(..., description="One of BUYER, BEEKEEPER, KVIC_ADMIN")

    @field_validator("phone")
    @classmethod
    def phone_must_be_digits(cls, v: str) -> str:
        if not v.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("Phone number must contain only digits (and optional +, -, spaces)")
        return v


class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


# ── Response schemas ───────────────────────────────────────────────────────
class UserResponse(BaseModel):
    """Safe user representation — password_hash is NEVER included."""

    id: int
    full_name: str
    email: str
    phone: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Response from POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
