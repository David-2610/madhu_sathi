"""
Shopping cart CRUD operations.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.honey_product import HoneyProduct, ProductStatus


def get_or_create_buyer_cart(db: Session, buyer_id: int) -> Cart:
    """Return the active cart for *buyer_id*, creating one if it does not yet exist."""
    cart = db.query(Cart).filter(Cart.buyer_id == buyer_id).first()
    if cart is None:
        cart = Cart(buyer_id=buyer_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def get_cart_item_by_product(db: Session, cart_id: int, product_id: int) -> Optional[CartItem]:
    """Find a cart item by cart_id and product_id."""
    return (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        .first()
    )


def add_item_to_cart(db: Session, cart: Cart, product_id: int) -> CartItem:
    """
    Add a product to *cart*.

    Caller must ensure product is valid, listed, and active before calling.
    """
    item = CartItem(cart_id=cart.id, product_id=product_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_item_from_cart(db: Session, cart: Cart, item_id: int) -> bool:
    """Remove a specific cart item from *cart*."""
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)
        .first()
    )
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def clear_cart(db: Session, cart: Cart) -> None:
    """Remove all items from *cart*."""
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
