"""
Authentication and RBAC endpoints.

Public endpoints (no token required):
    POST /auth/register  — create a new user account
    POST /auth/login     — authenticate and receive a JWT

Protected endpoints (Bearer JWT required):
    GET  /auth/me              — return the currently authenticated user

RBAC verification endpoints (temporary — Phase 3 only):
    GET  /auth/test/buyer      — accessible only by BUYER
    GET  /auth/test/beekeeper  — accessible only by BEEKEEPER
    GET  /auth/test/kvic-admin — accessible only by KVIC_ADMIN
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.core.security import create_access_token, verify_password
from app.crud.user import create_user, get_user_by_email
from app.db import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse, UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── POST /auth/register ────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    Register a new Honey Chain user.

    - Only BUYER and BEEKEEPER roles may self-register.
    - KVIC_ADMIN accounts must be provisioned through a separate admin flow.
    - Rejects duplicate email addresses with HTTP 409.
    - Stores only the bcrypt hash of the password — never plaintext.
    - Returns safe user information (no ``password_hash``).
    """
    # ── Block KVIC_ADMIN self-registration ──────────────────────────────
    _SELF_REGISTRABLE_ROLES = {UserRole.BUYER, UserRole.BEEKEEPER}
    if payload.role not in _SELF_REGISTRABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Public registration is not allowed for role '{payload.role.value}'. "
                "KVIC Admin accounts must be provisioned by an existing administrator."
            ),
        )

    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )
    return create_user(db, payload)


# ── POST /auth/login ───────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate with email + password.

    Returns a signed JWT access token and safe user information.

    A deliberately vague error (HTTP 401) is returned for both unknown email
    and wrong password — this prevents user-enumeration attacks.
    """
    _auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = get_user_by_email(db, payload.email)
    if user is None:
        raise _auth_error

    if not verify_password(payload.password, user.password_hash):
        raise _auth_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ── GET /auth/me ───────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the currently authenticated user",
)
def me(current_user: User = Depends(get_current_user)) -> User:
    """
    Return the profile of the user identified by the Bearer JWT.

    Requires a valid, non-expired access token.
    """
    return current_user


# ── RBAC verification endpoints (Phase 3 temporary) ───────────────────────
@router.get(
    "/test/buyer",
    summary="[RBAC test] Buyer-only endpoint",
    tags=["RBAC Test"],
)
def test_buyer(current_user: User = Depends(require_role(UserRole.BUYER))) -> dict:
    """Accessible ONLY to users with role BUYER."""
    return {"message": f"Hello Buyer {current_user.full_name}!"}


@router.get(
    "/test/beekeeper",
    summary="[RBAC test] Beekeeper-only endpoint",
    tags=["RBAC Test"],
)
def test_beekeeper(current_user: User = Depends(require_role(UserRole.BEEKEEPER))) -> dict:
    """Accessible ONLY to users with role BEEKEEPER."""
    return {"message": f"Hello Beekeeper {current_user.full_name}!"}


@router.get(
    "/test/kvic-admin",
    summary="[RBAC test] KVIC Admin-only endpoint",
    tags=["RBAC Test"],
)
def test_kvic_admin(current_user: User = Depends(require_role(UserRole.KVIC_ADMIN))) -> dict:
    """Accessible ONLY to users with role KVIC_ADMIN."""
    return {"message": f"Hello KVIC Admin {current_user.full_name}!"}
