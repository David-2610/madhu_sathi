"""
User CRUD operations.

Only the database operations live here — no business logic, no HTTP concerns.
"""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the User whose email matches *email*, or None."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return the User with the given *user_id*, or None."""
    return db.get(User, user_id)


def create_user(db: Session, payload: UserCreate) -> User:
    """
    Persist a new User to the database.

    The plaintext password in *payload* is hashed before storage.
    The caller is responsible for committing or rolling back the session.
    """
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),  # NEVER store plaintext
        role=payload.role.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
