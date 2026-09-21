"""
Payment ORM model.

Tracks payment intents, references, and capture states for orders.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.order import Order


class PaymentStatus(str, PyEnum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Payment(Base):
    """Financial transaction/payment record linked to an Order."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    payment_reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="paymentstatus", create_type=True),
        nullable=False,
        default=PaymentStatus.CREATED,
        index=True,
    )

    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    order: Mapped["Order"] = relationship("Order", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_payment_amount_pos"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Payment id={self.id!r} ref={self.payment_reference!r} status={self.status!r}>"
