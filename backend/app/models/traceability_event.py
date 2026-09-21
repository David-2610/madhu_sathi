"""
TraceabilityEvent ORM model.

Records immutable lifecycle milestones for batches and packaged units.
Each event stores a cryptographic SHA-256 hash and optional real blockchain transaction proof.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.honey_batch import HoneyBatch
    from app.models.honey_product import HoneyProduct


class TraceEventType(str, PyEnum):
    HARVEST_RECORDED = "HARVEST_RECORDED"
    BATCH_CREATED = "BATCH_CREATED"
    PROCESSING_RECORDED = "PROCESSING_RECORDED"
    QUALITY_TEST_ADDED = "QUALITY_TEST_ADDED"
    PACKAGED = "PACKAGED"
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_SOLD = "PRODUCT_SOLD"


class TraceabilityEvent(Base):
    """Immutable traceability event linked to a honey batch or product."""

    __tablename__ = "traceability_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_type: Mapped[TraceEventType] = mapped_column(
        Enum(TraceEventType, name="traceeventtype", create_type=True),
        nullable=False,
    )

    batch_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("honey_batches.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("honey_products.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cryptographic proof (SHA-256)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Real blockchain transaction hash (strictly None if mock or not broadcast)
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_on_chain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    batch: Mapped[Optional["HoneyBatch"]] = relationship("HoneyBatch", back_populates="events")
    product: Mapped[Optional["HoneyProduct"]] = relationship("HoneyProduct", back_populates="events")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TraceabilityEvent id={self.id!r} type={self.event_type!r} hash={self.event_hash[:8]}...>"
