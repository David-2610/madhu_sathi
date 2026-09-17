"""
Apiary ORM model.

Represents a bee farm / apiary location managed by a beekeeper.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.beekeeper import BeekeeperProfile
    from app.models.hive import Hive


class Apiary(Base):
    """Bee farm / apiary managed by a single beekeeper."""

    __tablename__ = "apiaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    beekeeper_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("beekeeper_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    beekeeper: Mapped["BeekeeperProfile"] = relationship(
        "BeekeeperProfile", back_populates="apiaries"
    )
    hives: Mapped[List["Hive"]] = relationship("Hive", back_populates="apiary")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Apiary id={self.id!r} name={self.name!r} beekeeper_id={self.beekeeper_id!r}>"
