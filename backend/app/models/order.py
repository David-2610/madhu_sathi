"""
Order and OrderItem ORM models.

Stores buyer purchase records and immutable snapshots of product state at time of order.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.honey_product import HoneyProduct
    from app.models.payment import Payment
    from app.models.user import User


class OrderStatus(str, PyEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUNDED = "REFUNDED"


class Order(Base):
    """Customer order placed by a BUYER."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    order_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    buyer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="orderstatus", create_type=True),
        nullable=False,
        default=OrderStatus.PENDING_PAYMENT,
        index=True,
    )

    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    shipping_address_json: Mapped[str] = mapped_column(Text, nullable=False)

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
    buyer: Mapped["User"] = relationship("User")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="order"
    )

    __table_args__ = (
        CheckConstraint("subtotal_amount >= 0", name="chk_order_subtotal_pos"),
        CheckConstraint("shipping_amount >= 0", name="chk_order_shipping_pos"),
        CheckConstraint("total_amount >= 0", name="chk_order_total_pos"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order id={self.id!r} number={self.order_number!r} status={self.status!r}>"


class OrderItem(Base):
    """
    Individual purchased item in an order.

    Preserves an immutable snapshot of all product and beekeeper origin details
    at the time of purchase, decoupling historical order records from live entity edits.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("honey_products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    # Snapshot fields
    product_serial: Mapped[str] = mapped_column(String(100), nullable=False)
    product_token: Mapped[str] = mapped_column(String(64), nullable=False)
    honey_type: Mapped[str] = mapped_column(String(100), nullable=False)
    net_weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    batch_code: Mapped[str] = mapped_column(String(100), nullable=False)
    beekeeper_code: Mapped[str] = mapped_column(String(50), nullable=False)
    beekeeper_name: Mapped[str] = mapped_column(String(255), nullable=False)
    apiary_name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["HoneyProduct"] = relationship("HoneyProduct")

    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="chk_order_item_price_pos"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrderItem id={self.id!r} order_id={self.order_id!r} serial={self.product_serial!r}>"
