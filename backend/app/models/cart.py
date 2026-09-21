"""
Cart and CartItem ORM models.

Maintains buyer active carts and item selections.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.honey_product import HoneyProduct
    from app.models.user import User


class Cart(Base):
    """Buyer active cart (1:1 with User)."""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    buyer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
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
    buyer: Mapped["User"] = relationship("User")
    items: Mapped[List["CartItem"]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Cart id={self.id!r} buyer_id={self.buyer_id!r}>"


class CartItem(Base):
    """Item added to a buyer's cart referencing an individual HoneyProduct."""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    cart_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("honey_products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    product: Mapped["HoneyProduct"] = relationship("HoneyProduct")

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CartItem id={self.id!r} cart_id={self.cart_id!r} product_id={self.product_id!r}>"
