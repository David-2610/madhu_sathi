"""
HoneyProduct ORM model.

Represents an individual physical packaged honey unit with a unique serial
and cryptographically secure opaque trace token.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.honey_batch import HoneyBatch
    from app.models.traceability_event import TraceabilityEvent


class ProductStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    REVOKED = "REVOKED"
    SUSPICIOUS = "SUSPICIOUS"


class HoneyProduct(Base):
    """Packaged honey jar / bottle with an opaque QR trace token."""

    __tablename__ = "honey_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("honey_batches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    serial_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    trace_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    net_weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    packaging_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="productstatus", create_type=True),
        nullable=False,
        default=ProductStatus.ACTIVE,
    )

    # Commerce & Marketplace fields
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    qr_code_svg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    batch: Mapped["HoneyBatch"] = relationship("HoneyBatch", back_populates="products")
    events: Mapped[List["TraceabilityEvent"]] = relationship(
        "TraceabilityEvent", back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("net_weight_g > 0", name="chk_product_net_weight_pos"),
        CheckConstraint("price IS NULL OR price >= 0", name="chk_product_price_non_neg"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<HoneyProduct id={self.id!r} serial={self.serial_number!r} status={self.status!r}>"

