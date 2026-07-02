"""
AlgoBounty database module — Supabase PostgreSQL as the primary database.

Uses the engine, models, and DDL from supabase_migration.py.
SQLite is available only as an explicit local-dev fallback when
SUPABASE_URL is not set.

Exports:
    init_db, SessionLocal, Base, engine, sync_engine, async_engine
    Agent, Bounty, GitHubPR, Notification
"""

import os
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Import the canonical Supabase implementation (reference DDL, models,
# engine builder, and async helpers).
# ---------------------------------------------------------------------------

from .supabase_migration import (
    Base,
    Agent,
    Bounty,
    GitHubPR,
    Notification,
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
    "engine",
    "sync_engine",
    "async_engine",
    "async_get_session",
]
