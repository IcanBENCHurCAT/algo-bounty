"""
AlgoBounty database module — Supabase PostgreSQL as the primary database.

Retrieves the database URL from the DATABASE_URL environment variable.
If the URL starts with "postgres://" (Supabase/Heroku default style),
automatically replaces it with "postgresql://" to comply with
SQLAlchemy 2.0 standards.

SQLite fallback (sqlite:///./algobounty.db) is used when DATABASE_URL
is not set or explicitly starts with "sqlite".

When using PostgreSQL, connect_args (e.g. check_same_thread=False) is
never applied — that flag is SQLite-specific.

Exports:
    init_db, SessionLocal, Base, engine, sync_engine, async_engine
    Agent, Bounty, GitHubPR, Notification
"""

from .supabase_migration import (
    Base,
    Agent,
    Bounty,
    GitHubPR,
    Notification,
    Arbitrator,
    DisputeArbitrator,
    WebhookDeliveryRecord,
    sync_engine,
    async_engine,
    engine,  # backward-compatible alias (async_engine)
    init_db,
    SessionLocal,
)
from .supabase_migration import async_get_session

# ---------------------------------------------------------------------------
# Re-export for compatibility with gateway/main.py and other callers.
# ---------------------------------------------------------------------------

__all__ = [
    "init_db",
    "SessionLocal",
    "Base",
    "Agent",
    "Bounty",
    "GitHubPR",
    "Notification",
    "Arbitrator",
    "DisputeArbitrator",
    "WebhookDeliveryRecord",
    "engine",
    "sync_engine",
    "async_engine",
    "async_get_session",
]
