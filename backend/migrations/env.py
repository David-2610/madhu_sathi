"""
Alembic environment script.

DATABASE_URL is read from the application settings (which reads from .env),
so there is a single source of truth for the connection string — no
credentials are hardcoded here.

HOW TO ADD NEW MODELS (future phases):
  1. Define the model in ``app/models/<name>.py`` inheriting from ``app.db.Base``.
  2. Add an import for it in ``app/models/__init__.py``.
  The import of ``app.models`` below will pull it in automatically.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Single source of truth for DATABASE_URL ───────────────────────────────
from app.core.config import get_settings

# ── Import Base + ALL models so autogenerate can detect schema changes ─────
from app.db import Base       # noqa: F401
import app.models             # noqa: F401  ← registers all models with Base.metadata

config = context.config
settings = get_settings()

# Override sqlalchemy.url from alembic.ini with the value from .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ── Logging ───────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Autogenerate target ───────────────────────────────────────────────────
target_metadata = Base.metadata


# ── Migration runners ─────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires a live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
