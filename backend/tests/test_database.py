"""
Database connectivity integration test.

Tests the SQLAlchemy engine connection only.
The HealthCheckRecord-specific tests from Phase 2 have been removed because
that table was dropped via migration in Phase 3.

If PostgreSQL is unavailable, the test is skipped with a clear message.
"""

import pytest
from sqlalchemy import text

from app.db import check_db_connection, engine


# ── Availability guard ─────────────────────────────────────────────────────
skip_if_no_db = pytest.mark.skipif(
    not check_db_connection(),
    reason="PostgreSQL is not reachable — skipping database integration tests.",
)


# ── Tests ──────────────────────────────────────────────────────────────────
@skip_if_no_db
def test_db_engine_connects():
    """Engine must successfully execute SELECT 1."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    assert result == 1


@skip_if_no_db
def test_users_table_exists():
    """The users table must exist (created by Phase 3 migration)."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables"
                "  WHERE table_name = 'users'"
                ")"
            )
        ).scalar()
    assert result is True, "Table 'users' does not exist — run: alembic upgrade head"
