"""
Alembic environment configuration for async SQLAlchemy + PostgreSQL.

This env.py runs under Alembic (synchronous CLI) but configures SQLAlchemy
to use the sync PostgreSQL driver so migrations execute properly.
"""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Add project root to sys.path so ``gateway`` imports work from here.
# This file lives at gateway/migrations/env.py → parent is gateway/ → parent is project root.
# ---------------------------------------------------------------------------
project_root = os.path.join(os.path.dirname(__file__), "..", "..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ---------------------------------------------------------------------------
# Import the SQLAlchemy models so Alembic can autodetect changes
# ---------------------------------------------------------------------------
try:
    from gateway.database import Base  # noqa: F401
except ImportError:
    Base = None

target_metadata = None
if Base is not None:
    target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    Generates SQL statements from the models, to be applied via the
    database driver.  The DATABASE_URL is read from env.
    """
    url = os.getenv("DATABASE_URL", "postgresql://algobounty:password@localhost/algobounty")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version",
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    We use the sync PostgreSQL driver so Alembic's synchronous API works.
    """
    from sqlalchemy import create_engine

    url = os.getenv("DATABASE_URL", "postgresql://algobounty:password@localhost/algobounty")

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version",
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
