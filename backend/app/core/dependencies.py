"""
FastAPI dependencies for authentication and role-based access control.

Public API:
    get_current_user  — requires a valid Bearer JWT; returns the authenticated User
    require_role      — factory that wraps get_current_user and enforces allowed roles
"""

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud.user import get_user_by_id
from app.db import get_db
from app.models.user import User
from app.schemas.user import UserRole

# ── Bearer token extractor ─────────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=True)


# ── get_current_user ───────────────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — validates the Bearer JWT and returns the active User.

    Raises HTTP 401 for:
    - Missing / malformed token
    - Expired token
    - User not found in the database

    Raises HTTP 403 for:
    - Inactive (soft-deleted) accounts
    """
    _credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = decode_access_token(credentials.credentials)
    except JWTError:
        raise _credentials_exception

    user = get_user_by_id(db, user_id)
    if user is None:
        raise _credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    return user


# ── require_role ───────────────────────────────────────────────────────────
def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Factory that returns a FastAPI dependency enforcing role-based access.

    Usage::

        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_role(UserRole.KVIC_ADMIN))):
            ...

    A valid, active user with the wrong role receives HTTP 403.
    """
    allowed_values = {r.value for r in allowed_roles}

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): "
                    f"{', '.join(allowed_values)}. "
                    f"Your role: {current_user.role}."
                ),
            )
        return current_user

    return _check
