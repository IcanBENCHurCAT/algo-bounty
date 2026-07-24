"""
Supabase-compatible migration module for AlgoBounty.

Builds a SQLAlchemy engine from the SUPABASE_URL environment variable.
If SUPABASE_URL is not set, falls back to SQLite for local development.

Usage:
    export SUPABASE_URL="postgresql://...supabase.co:5432/postgres"
    python gateway/supabase_migration.py
"""

import os
import signal
from datetime import datetime, timezone
from .config import settings

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    event,
    create_engine,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Connection pool warming (reduces first-request latency)
# ---------------------------------------------------------------------------


def _warm_pool(_conn, record):
    """Create one extra connection at startup so first requests don't stall."""
    pass  # SQLAlchemy handles pool initialization; keep for event listeners

# ---------------------------------------------------------------------------
# Engine construction
# ---------------------------------------------------------------------------

SUPABASE_URL = settings.SUPABASE_URL
DATABASE_URL = settings.DATABASE_URL


def _normalize_db_url(url: str) -> str:
    """Normalize a database URL for SQLAlchemy 2.0 compatibility.

    Replaces "postgres://" with "postgresql://" because
    SQLAlchemy 2.0 no longer accepts the bare "postgres://" scheme.
    Leaves "postgresql://" and "sqlite:///" URLs unchanged.
    """
    if url and url.startswith("postgres://") and not url.startswith("postgresql://"):
        return "postgresql" + url[len("postgres"):]
    return url


def build_engine():
    """Return (async_engine, sync_engine) — PostgreSQL via Supabase or SQLite fallback.

    DATABASE_URL is read from the environment (via config.py settings).
    If the URL starts with "postgres://", it is automatically converted
    to "postgresql://" to comply with SQLAlchemy 2.0.

    SQLite fallback (sqlite:///./algobounty.db) is used when
    DATABASE_URL is not set or is explicitly an SQLite URL.
    """

    # Use DATABASE_URL for database connection; do not use HTTP SUPABASE_URL
    url = DATABASE_URL
    if not url and SUPABASE_URL and not SUPABASE_URL.startswith("http"):
        url = SUPABASE_URL

    if url:
        url = _normalize_db_url(url)

    if url and ("supabase" in url.lower() or url.startswith("postgresql")):
        # PostgreSQL (Supabase or generic)
        return _build_postgres_engine(url, is_asyncpg=True)
    else:
        # Fallback: SQLite for local dev
        sqlite_url = "sqlite:///./algobounty.db"
        return _build_sqlite_engine(sqlite_url)


def _build_postgres_engine(url: str, is_asyncpg: bool = True):
    """Build async + sync PostgreSQL engines from a Supabase / PG URL."""
    if is_asyncpg:
        # Ensure the async URL uses the postgresql+asyncpg:// scheme
        if url.startswith("postgresql://"):
            _async_url = url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            _async_url = url

        # Strip +asyncpg suffix for sync engine so SQLAlchemy picks the
        # synchronous driver automatically.
        _sync_url = _async_url.replace("postgresql+asyncpg://", "postgresql://")

        pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

        async_engine = create_async_engine(
            _async_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
            connect_args={"timeout": connect_timeout},
            echo=False,
        )

        sync_engine = create_engine(
            _sync_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
            connect_args={"connect_timeout": connect_timeout},
            echo=False,
        )
        event.listen(sync_engine, "connect", _warm_pool)
    else:
        # Pure sync PostgreSQL (no asyncpg)
        connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))
        sync_engine = create_engine(
            url,
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
            connect_args={"connect_timeout": connect_timeout},
            echo=False,
        )
        event.listen(sync_engine, "connect", _warm_pool)
        async_engine = None

    return async_engine, sync_engine


def _build_sqlite_engine(url: str):
    """Build async + sync SQLite engines (local dev).

    Falls back to sync-only if aiosqlite is not installed.
    """
    try:
        async_engine = create_async_engine(
            url.replace("sqlite://", "sqlite+aiosqlite://"),
            connect_args={"check_same_thread": False},
        )
    except (ModuleNotFoundError, ImportError):
        # aiosqlite not available — sync-only fallback
        async_engine = None
        print("[supabase_migration] aiosqlite not installed; using sync-only SQLite")

    sync_engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
    )
    return async_engine, sync_engine


# ---------------------------------------------------------------------------
# Exposed globals (mimics database.py interface)
# ---------------------------------------------------------------------------

async_engine, sync_engine = build_engine()
# Backward-compatible alias
engine = async_engine


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
    github_username    VARCHAR UNIQUE,
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
    platform_fee      INTEGER DEFAULT 200,
    treasury_address  VARCHAR DEFAULT 'RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5',
    gateway_address   VARCHAR,
    authorized_app_id INTEGER,
    hitm_enforced     BOOLEAN DEFAULT FALSE
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

-- Arbitrators: registered high-karma agents
CREATE TABLE IF NOT EXISTS arbitrators (
    address            VARCHAR PRIMARY KEY,
    status             VARCHAR DEFAULT 'active',
    registered_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Dispute-arbitrator assignments and votes
CREATE TABLE IF NOT EXISTS dispute_arbitrators (
    id                 SERIAL PRIMARY KEY,
    bounty_id          VARCHAR REFERENCES bounties(bounty_id) ON DELETE CASCADE,
    arbitrator_address VARCHAR REFERENCES arbitrators(address) ON DELETE CASCADE,
    vote               VARCHAR,
    voted_at           TIMESTAMPTZ,
    UNIQUE(bounty_id, arbitrator_address)
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
CREATE INDEX IF NOT EXISTS idx_dispute_arbitrators_bounty_id ON dispute_arbitrators (bounty_id);
CREATE INDEX IF NOT EXISTS idx_dispute_arbitrators_arbitrator ON dispute_arbitrators (arbitrator_address);

-- Idempotency tracking for GitHub webhook deliveries (prevents duplicate payout)
CREATE TABLE IF NOT EXISTS webhook_delivery_records (
    id           SERIAL PRIMARY KEY,
    delivery_id  VARCHAR NOT NULL UNIQUE,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    status       VARCHAR DEFAULT 'success'
);
CREATE INDEX IF NOT EXISTS idx_webhook_delivery_delivery_id ON webhook_delivery_records (delivery_id);
"""


# ---------------------------------------------------------------------------
# Sync helper
# ---------------------------------------------------------------------------

def init_db():
    """Create tables (if using SQLite) or run Alembic (if using Supabase/PG).

    Resilient to connection failures — if the database is unreachable,
    the gateway still starts and falls back to in-memory/error handling.
    """
    if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
        # SQLite: just create the tables
        Base.metadata.create_all(sync_engine)
        _seed_platform_account()
    else:
        # PostgreSQL / Supabase: run Alembic migrations (with timeout)
        import subprocess
        import os as _os

        alembic_cfg = _os.path.join(
            _os.path.dirname(__file__), "alembic.ini"
        )
        try:
            _run_alembic_with_timeout(alembic_cfg)
        except (SystemExit, Exception) as exc:
            print(f"[supabase_migration] Alembic migration failed: {exc}. Falling back to Base.metadata.create_all.")
            try:
                Base.metadata.create_all(sync_engine)
            except Exception as create_exc:
                print(f"[supabase_migration] create_all fallback failed: {create_exc}")
            _seed_platform_account()


def _run_alembic_with_timeout(alembic_cfg, timeout=10):
    """Run Alembic upgrade with a hard timeout to prevent hangs."""
    import alembic.config
    import alembic.command

    if hasattr(signal, "SIGALRM"):
        def handler(signum, frame):
            raise TimeoutError("alembic upgrade timed out")

        old_handler = signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)
        try:
            cfg = alembic.config.Config(alembic_cfg)
            alembic.command.upgrade(cfg, "head")
        finally:
            signal.alarm(0)  # Cancel the alarm
            signal.signal(signal.SIGALRM, old_handler)  # Restore handler
    else:
        # Fallback for Windows where SIGALRM is not supported
        cfg = alembic.config.Config(alembic_cfg)
        alembic.command.upgrade(cfg, "head")


def _seed_platform_account():
    """Seed the platform admin agent if the DB is empty.

    Non-fatal on connection failure — the gateway can still serve requests.
    """
    try:
        db = SessionLocal()
        try:
            from gateway.supabase_migration import Agent

            platform_address = (
                "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5"
            )
            if not db.query(Agent).filter(
                Agent.address == platform_address
            ).first():
                db.add(Agent(address=platform_address, karma=100))
                db.commit()
        except Exception as exc:
            print(f"[supabase_migration] seed_platform_account skipped: {exc}")
            db.rollback()
        finally:
            db.close()
    except Exception as exc:
        print(f"[supabase_migration] session unavailable (DB may be unreachable): {exc}")


Base = declarative_base()


# ---------------------------------------------------------------------------
# Models (same as original database.py)
# ---------------------------------------------------------------------------


class Agent(Base):
    __tablename__ = "agents"
    address = Column(String, primary_key=True, index=True)
    github_username = Column(String, unique=True, nullable=True)
    karma = Column(Integer, default=25)
    completed_bounties = Column(Integer, default=0)
    disputes_lost = Column(Integer, default=0)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Bounty(Base):
    __tablename__ = "bounties"
    bounty_id = Column(String, primary_key=True, index=True)
    app_id = Column(Integer, unique=True, index=True, nullable=True)
    status = Column(String, default="open")
    creator = Column(String, index=True, nullable=False)
    worker = Column(String, index=True, nullable=True)
    amount = Column(BigInteger)
    asset_id = Column(Integer, default=0)
    is_hitm = Column(Boolean, default=False)
    description = Column(String)
    repo_url = Column(String, index=True, nullable=False)
    karma_requirement = Column(Integer, default=0)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    deadline_round = Column(Integer, nullable=True)
    hitm_review_days = Column(Integer, default=7)
    rejection_count = Column(Integer, default=0)
    payout_type = Column(String, nullable=True)
    treasury_altered = Column(Boolean, default=False, nullable=False)
    platform_fee = Column(Integer, default=200, nullable=False)
    treasury_address = Column(String(58), default="RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5", nullable=False)
    gateway_address = Column(String(58), nullable=True)
    authorized_app_id = Column(Integer, nullable=True)
    hitm_enforced = Column(Boolean, default=False, nullable=False)



class GitHubPR(Base):
    __tablename__ = "github_prs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pr_number = Column(Integer, index=True, nullable=False)
    repo_url = Column(String, index=True, nullable=False)
    bounty_id = Column(String, ForeignKey("bounties.bounty_id"), nullable=False)
    state = Column(String, default="open")
    author = Column(String, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipient = Column(String, index=True, nullable=False)
    message = Column(String, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Arbitrator(Base):
    __tablename__ = "arbitrators"
    address = Column(String, primary_key=True, index=True)
    status = Column(String, default="active", nullable=False)
    registered_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DisputeArbitrator(Base):
    __tablename__ = "dispute_arbitrators"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bounty_id = Column(String, ForeignKey("bounties.bounty_id", ondelete="CASCADE"), nullable=False)
    arbitrator_address = Column(String, ForeignKey("arbitrators.address", ondelete="CASCADE"), nullable=False)
    vote = Column(String, nullable=True)
    voted_at = Column(DateTime, nullable=True)


class WebhookDeliveryRecord(Base):
    """Idempotency guard: stores processed X-GitHub-Delivery IDs to prevent
    duplicate trustless payout transactions on webhook re-delivery (FR-004)."""
    __tablename__ = "webhook_delivery_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    delivery_id = Column(String, unique=True, index=True, nullable=False)
    processed_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status = Column(String, default="success", nullable=False)


# ---------------------------------------------------------------------------
# Session & async helpers
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=sync_engine
)


async def async_get_session():
    """Yield an async SQLAlchemy session."""
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"DATABASE_URL: {DATABASE_URL or '(using SUPABASE_URL)'}")
    print(f"SUPABASE_URL: {SUPABASE_URL or '(not set)'}")
    print()

    if SUPABASE_URL or DATABASE_URL:
        print("PostgreSQL/Supabase mode active.")
    else:
        print("SQLite fallback active (local dev).")
    print()

    print("--- Table DDL (copy to Supabase SQL Editor) ---")
    print(CREATE_TABLES_SQL)
    print()
    print("--- Run with: export SUPABASE_URL=... && python supabase_migration.py ---")
