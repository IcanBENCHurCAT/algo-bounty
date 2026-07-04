"""
Supabase-compatible migration utility for AlgoBounty.

Provides the canonical DDL for manual Supabase setup and a standalone
runner to trigger migrations or view the schema.
"""

from .database import (
    Base,
    Agent,
    Bounty,
    GitHubPR,
    Notification,
    sync_engine,
    async_engine,
    engine,
    init_db,
    SessionLocal,
    async_get_session,
)
from .config import settings

# ---------------------------------------------------------------------------
# Table DDL — SQL to create tables directly in Supabase
# ---------------------------------------------------------------------------

CREATE_TABLES_SQL = """
-- ================================================================
-- AlgoBounty Tables for Supabase / PostgreSQL
-- Run this in Supabase SQL Editor or via psql to create the schema.
-- ================================================================

-- Agents: bounty hunters / workers
CREATE TABLE IF NOT EXISTS agents (
    address            VARCHAR PRIMARY KEY,
    karma              INTEGER DEFAULT 25,
    completed_bounties INTEGER DEFAULT 0,
    disputes_lost      INTEGER DEFAULT 0,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Bounties: reward offers on the platform
CREATE TABLE IF NOT EXISTS bounties (
    bounty_id         VARCHAR PRIMARY KEY,
    app_id            INTEGER UNIQUE,
    status            VARCHAR DEFAULT 'open',
    creator           VARCHAR NOT NULL,
    worker            VARCHAR,
    amount            BIGINT NOT NULL,
    asset_id          INTEGER DEFAULT 0,
    is_hitm           BOOLEAN DEFAULT FALSE,
    description       TEXT,
    repo_url          VARCHAR,
    karma_requirement INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    deadline_round    INTEGER,
    hitm_review_days  INTEGER DEFAULT 7,
    rejection_count   INTEGER DEFAULT 0,
    payout_type       VARCHAR
);

-- GitHub Pull Requests linked to bounties
CREATE TABLE IF NOT EXISTS github_prs (
    id          SERIAL PRIMARY KEY,
    pr_number   INTEGER NOT NULL,
    repo_url    VARCHAR NOT NULL,
    bounty_id   VARCHAR REFERENCES bounties(bounty_id),
    state       VARCHAR DEFAULT 'open',
    author      VARCHAR,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications sent to users
CREATE TABLE IF NOT EXISTS notifications (
    id          SERIAL PRIMARY KEY,
    recipient   VARCHAR NOT NULL,
    message     TEXT NOT NULL,
    read        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_bounties_creator        ON bounties (creator);
CREATE INDEX IF NOT EXISTS idx_bounties_repo_url       ON bounties (repo_url);
CREATE INDEX IF NOT EXISTS idx_bounties_status         ON bounties (status);
CREATE INDEX IF NOT EXISTS idx_bounties_karma          ON bounties (karma_requirement);
CREATE INDEX IF NOT EXISTS idx_github_prs_pr_number    ON github_prs (pr_number);
CREATE INDEX IF NOT EXISTS idx_github_prs_repo_url     ON github_prs (repo_url);
CREATE INDEX IF NOT EXISTS idx_github_prs_bounty_id    ON github_prs (bounty_id);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications (recipient);
"""

# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    url = settings.DATABASE_URL or settings.SUPABASE_URL or os.environ.get("DATABASE_URL")

    print(f"DATABASE_URL: {settings.DATABASE_URL or '(not set)'}")
    print(f"SUPABASE_URL: {settings.SUPABASE_URL or '(not set)'}")
    print()

    if url and ("supabase" in url.lower() or "postgresql" in url.lower()):
        print("PostgreSQL/Supabase mode active.")
    else:
        print("SQLite fallback active (local dev).")
    print()

    print("--- Table DDL (copy to Supabase SQL Editor) ---")
    print(CREATE_TABLES_SQL)
    print()
    print("--- Run with: export DATABASE_URL=... && python -m gateway.supabase_migration ---")
