"""
Security utilities: password hashing and JWT management.

RULES enforced here:
- Passwords are NEVER stored as plaintext.
- JWT_SECRET_KEY is ALWAYS read from environment (never hardcoded).
- Tokens expire after JWT_ACCESS_TOKEN_EXPIRE_MINUTES (default 60 min).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ── Password hashing ───────────────────────────────────────────────────────
# bcrypt is the recommended algorithm — intentionally slow to resist brute-force.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return the bcrypt hash of *plain_password*. Never store the original."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT ────────────────────────────────────────────────────────────────────
_TOKEN_SUBJECT_PREFIX = "user:"


def create_access_token(user_id: int) -> str:
    """
    Create a signed JWT access token that identifies *user_id*.

    The token contains:
    - ``sub``: "user:<id>"
    - ``exp``: expiry timestamp (UTC)
    - ``iat``: issued-at timestamp (UTC)
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": f"{_TOKEN_SUBJECT_PREFIX}{user_id}",
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """
    Validate *token* and return the user ID encoded in its ``sub`` claim.

    Raises ``JWTError`` if the token is invalid, expired, or tampered.
    """
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    sub: str | None = payload.get("sub")
    if not sub or not sub.startswith(_TOKEN_SUBJECT_PREFIX):
        raise JWTError("Invalid token subject")
    return int(sub[len(_TOKEN_SUBJECT_PREFIX):])
