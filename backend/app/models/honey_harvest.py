"""
HoneyHarvest ORM model.

Represents a harvest event from a specific hive.

DOMAIN INVARIANT:
Excess production must NEVER be labeled as adulteration.
Differences between estimated and actual yield are normal agricultural
phenomena; any statistical anomaly is flagged later as
PRODUCTION_ANOMALY / INVESTIGATION_REQUIRED, not adulteration.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.hive import Hive
    from app.models.honey_batch import HoneyBatch


class HoneyHarvest(Base):
    """Honey harvest record originating from a single hive."""

    __tablename__ = "honey_harvests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    harvest_date: Mapped[date] = mapped_column(Date, nullable=False)
    estimated_quantity_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    honey_type: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    hive: Mapped["Hive"] = relationship("Hive", back_populates="harvests")
    batches: Mapped[List["HoneyBatch"]] = relationship(
        "HoneyBatch", back_populates="harvest"
    )

    __table_args__ = (
        CheckConstraint("actual_quantity_kg >= 0", name="chk_harvest_actual_qty_nonneg"),
        CheckConstraint(
            "estimated_quantity_kg IS NULL OR estimated_quantity_kg >= 0",
            name="chk_harvest_estimated_qty_nonneg",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<HoneyHarvest id={self.id!r} hive_id={self.hive_id!r} actual={self.actual_quantity_kg!r}kg>"
