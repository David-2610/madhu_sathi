"""
Database layer — public interface.

Exports:
    engine          — SQLAlchemy Engine bound to DATABASE_URL
    SessionLocal    — sessionmaker factory
    Base            — DeclarativeBase; all ORM models inherit from this
    get_db          — FastAPI dependency that yields a scoped Session
    check_db_connection — lightweight startup connectivity probe
"""

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine ─────────────────────────────────────────────────────────────────
# pool_pre_ping transparently reconnects after idle-connection drops.
# echo is restricted to development so production logs stay clean.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.APP_ENV == "development",
)

# ── Session factory ────────────────────────────────────────────────────────
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoids lazy-load errors after commit
)


# ── Declarative base ───────────────────────────────────────────────────────
# All ORM models (current and future phases) must inherit from Base so that
# Alembic autogenerate can detect schema changes automatically.
class Base(DeclarativeBase):
    pass


# ── FastAPI session dependency ─────────────────────────────────────────────
def get_db():
    """
    Yield a SQLAlchemy ``Session`` and guarantee it is closed after the
    request completes (success or error).

    Usage inside a route::

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.db import get_db

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Connectivity probe ─────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """
    Execute a lightweight ``SELECT 1`` to verify the database is reachable.

    Returns ``True`` on success, ``False`` on any error.
    Used by the lifespan handler in ``app.main`` to log a startup warning
    when the database is unavailable.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Database connectivity check failed: %s", exc)
        return False
