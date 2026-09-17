"""
HoneyBatch ORM model.

Represents a processed batch of honey originating from a specific harvest.
"""

from datetime import date, datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.beekeeper import BeekeeperProfile
    from app.models.honey_harvest import HoneyHarvest
    from app.models.honey_product import HoneyProduct
    from app.models.traceability_event import TraceabilityEvent


class BatchStatus(str, PyEnum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    SOLD = "SOLD"
    RECALLED = "RECALLED"


class HoneyBatch(Base):
    """Honey batch originating from a honey harvest."""

    __tablename__ = "honey_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    batch_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    beekeeper_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("beekeeper_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    harvest_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("honey_harvests.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    batch_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    honey_type: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, name="batchstatus", create_type=True),
        nullable=False,
        default=BatchStatus.CREATED,
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
    beekeeper: Mapped["BeekeeperProfile"] = relationship(
        "BeekeeperProfile", back_populates="batches"
    )
    harvest: Mapped["HoneyHarvest"] = relationship(
        "HoneyHarvest", back_populates="batches"
    )
    products: Mapped[List["HoneyProduct"]] = relationship(
        "HoneyProduct", back_populates="batch"
    )
    events: Mapped[List["TraceabilityEvent"]] = relationship(
        "TraceabilityEvent", back_populates="batch"
    )

    __table_args__ = (
        CheckConstraint("quantity_kg >= 0", name="chk_batch_qty_nonneg"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<HoneyBatch id={self.id!r} code={self.batch_code!r} qty={self.quantity_kg!r}kg status={self.status!r}>"
