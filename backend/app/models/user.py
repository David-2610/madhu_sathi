"""
User ORM model.

Stores registered users for all three roles: BUYER, BEEKEEPER, KVIC_ADMIN.

SECURITY NOTES:
- ``password_hash`` stores only the bcrypt hash — NEVER the plaintext password.
- ``email`` has a unique constraint and an index for fast lookup during login.
- ``role`` is restricted to the PostgreSQL enum type ``userrole``.
- ``is_active`` allows soft-disabling accounts without deleting them.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.schemas.user import UserRole

if TYPE_CHECKING:
    from app.models.beekeeper import BeekeeperProfile


class User(Base):
    """Registered Honey Chain user (any role)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    full_name: Mapped[str] = mapped_column(String(100), nullable=False)

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,      # database-level uniqueness constraint
        index=True,       # fast lookup during login
    )

    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # NEVER store the raw password — only the bcrypt hash
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        Enum(UserRole, name="userrole", create_type=True),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    beekeeper_profile: Mapped[Optional["BeekeeperProfile"]] = relationship(
        "BeekeeperProfile", back_populates="user", uselist=False
    )

    # Extra index on (email, is_active) to speed up active-user login queries
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id!r} email={self.email!r} role={self.role!r}>"
