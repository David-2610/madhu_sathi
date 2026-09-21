"""
BeekeeperProfile ORM model.

Represents the profile of a registered user whose role is BEEKEEPER.
Linked 1-to-1 with the `users` table.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.apiary import Apiary
    from app.models.honey_batch import HoneyBatch
    from app.models.user import User


class BeekeeperProfile(Base):
    """Profile for an authenticated user with role BEEKEEPER."""

    __tablename__ = "beekeeper_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )

    beekeeper_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    village: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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
    user: Mapped["User"] = relationship("User", back_populates="beekeeper_profile")
    apiaries: Mapped[List["Apiary"]] = relationship(
        "Apiary", back_populates="beekeeper"
    )
    batches: Mapped[List["HoneyBatch"]] = relationship(
        "HoneyBatch", back_populates="beekeeper"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BeekeeperProfile id={self.id!r} code={self.beekeeper_code!r} user_id={self.user_id!r}>"
