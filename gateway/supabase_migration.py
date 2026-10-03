"""
Supabase-compatible migration module for AlgoBounty.

Builds a SQLAlchemy engine from the SUPABASE_URL environment variable.
If SUPABASE_URL is not set, falls back to SQLite for local development.

Usage:
    export SUPABASE_URL="postgresql://...supabase.co:5432/postgres"
    python gateway/supabase_migration.py
"""

import hashlib
import os
import signal
from datetime import datetime, timezone
from .config import settings

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    create_engine,
    DECIMAL,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ─── ToS version / governing law constants (Legal #171) ─────────────────
CURRENT_TOS_VERSION = "1.1.0"  # bumped from 1.0.0 to add enforceability
PLATFORM_GOVERNING_LAW = "Delaware, USA"  # Constitution §5.8 fallback
PLATFORM_ARBITRATION_PROC = "mediation_then_binding"  # FAA-governed

# Pre-compute ToS text hash for tamper-evident chain
_TOS_TEXT_1_1_0 = (
    "AlgoBounty Terms of Service v1.1.0 "
    "- Pre-Mainnet Protocol Stewardship. "
    "Governing law: Delaware, USA. "
    "Arbitration: FAA-governed mediation then binding. "
    "Non-custodial software protocol. "
    "Counterparty compliance and taxes per §3. "
    "Mandatory arbitration under FAA per §4. "
    "Dispute resolution: evaluator ruling → platform blacklist/flag via KYA. "
    "Mediation-then-binding process for all platform disputes."
)
CURRENT_TOS_HASH = hashlib.sha256(_TOS_TEXT_1_1_0.encode()).hexdigest()

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

-- ─── Terms of Service Enforcement (Legal #171) ──────────────────

CREATE TABLE IF NOT EXISTS user_terms_acceptance (
    id                  SERIAL PRIMARY KEY,
    address             VARCHAR NOT NULL REFERENCES agents(address),
    terms_version       VARCHAR NOT NULL,
    accepted_at         TIMESTAMPTZ DEFAULT NOW(),
    accepted_ip_hash    VARCHAR,
    user_agent_hash     VARCHAR,
    UNIQUE(address, terms_version)
);
CREATE INDEX IF NOT EXISTS idx_user_terms_address ON user_terms_acceptance (address);

CREATE TABLE IF NOT EXISTS terms_history (
    id              SERIAL PRIMARY KEY,
    version         VARCHAR UNIQUE NOT NULL,
    text            TEXT NOT NULL,
    sha256_hash     VARCHAR UNIQUE NOT NULL,
    effective_date  TIMESTAMPTZ DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    governing_law  VARCHAR DEFAULT 'Delaware, USA',
    arbitration_clause TEXT DEFAULT 'mediation_then_binding'
);

-- Seed the current ToS v1.1.0
INSERT INTO terms_history (version, text, sha256_hash, effective_date, is_active, governing_law, arbitration_clause)
VALUES (
    '1.1.0',
    'AlgoBounty Terms of Service v1.1.0 - Pre-Mainnet Protocol Stewardship. Governing law: Delaware, USA. Arbitration: FAA-governed mediation then binding. Non-custodial software protocol. Counterparty compliance and taxes per §3. Mandatory arbitration under FAA per §4. Dispute resolution: evaluator ruling → platform blacklist/flag via KYA. Mediation-then-binding process for all platform disputes.',
    (SELECT CURRENT_TOS_HASH FROM (
        SELECT md5('dummy') as CURRENT_TOS_HASH
    ) tmp),
    NOW(),
    TRUE,
    'Delaware, USA',
    'mediation_then_binding'
);

-- Blacklist / Quarantine (Legal #171 + #172)
CREATE TABLE IF NOT EXISTS user_blacklist (
    id              SERIAL PRIMARY KEY,
    address         VARCHAR UNIQUE NOT NULL REFERENCES agents(address),
    reason          VARCHAR NOT NULL,
    details         TEXT,
    blacklisted_at  TIMESTAMPTZ DEFAULT NOW(),
    blacklisted_by  VARCHAR REFERENCES agents(address),
    expires_at      TIMESTAMPTZ,
    status          VARCHAR DEFAULT 'active',
    resolved_by     VARCHAR,
    resolved_at     TIMESTAMPTZ,
    resolution_note TEXT
);
CREATE INDEX IF NOT EXISTS idx_blacklist_address ON user_blacklist (address);
CREATE INDEX IF NOT EXISTS idx_blacklist_status ON user_blacklist (status);

-- Agents: bounty hunters / workers
CREATE TABLE IF NOT EXISTS agents (
    address                      VARCHAR PRIMARY KEY,
    github_username              VARCHAR UNIQUE,
    karma                        INTEGER DEFAULT 25,
    completed_bounties           INTEGER DEFAULT 0,
    disputes_lost                INTEGER DEFAULT 0,
    created_at                   TIMESTAMPTZ DEFAULT NOW(),
    -- Stewardship fields (Legal #165)
    steward_name                 VARCHAR,
    steward_email                VARCHAR,
    steward_verified             BOOLEAN DEFAULT FALSE,
    steward_stablecoin_address   VARCHAR(58),
    steward_of                   VARCHAR,
    steward_of_steward_address   VARCHAR(58),
    -- Tax compliance fields (Legal #170)
    tax_jurisdiction             VARCHAR(4),   -- ISO 3166-1 alpha-2 (US, DE, GB, etc.)
    tax_form_submitted           BOOLEAN DEFAULT FALSE,
    tax_form_date                TIMESTAMPTZ,
    cumulative_payouts_year      DOUBLE PRECISION DEFAULT 0.0,
    tax_withhold_rate            DOUBLE PRECISION DEFAULT 0.0
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

    # ─── Stewardship fields (Legal #165) ─────────────────────────────────
    steward_name = Column(String, nullable=True)        # human name
    steward_email = Column(String, nullable=True)       # contact email
    steward_verified = Column(Boolean, default=False)   # KYA / manual verified?
    steward_stablecoin_address = Column(String(58), nullable=True)  # USDC/etc for liability routing
    steward_of = Column(String, nullable=True)          # link multiple agents to same steward (group key)
    steward_of_steward_address = Column(String(58), nullable=True)  # the steward's wallet address

    # ─── Tax compliance fields (Legal #170) ─────────────────────────────
    tax_jurisdiction = Column(String(4), nullable=True)  # ISO 3166-1 alpha-2
    tax_form_submitted = Column(Boolean, default=False)  # W-9 or W-8BEN
    tax_form_date = Column(DateTime, nullable=True)       # ISO 8601 submission date
    cumulative_payouts_year = Column(Float(asdecimal=False), default=0.0)  # YTD USD for 1099-K
    tax_withhold_rate = Column(Float, default=0.0)       # withholding rate (0-1)

    # ─── Cold-start fields (Karma #175) ───────────────────────────
    has_collateral = Column(Boolean, default=False)       # has active collateral deposit
    vouched_by_count = Column(Integer, default=0)         # number of active vouches received
    cold_start_eligible = Column(Boolean, default=True)   # eligible for collateral/staged path


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
    payout_ready = Column(Boolean, default=False, nullable=False)
    payout_ready_at = Column(DateTime, nullable=True)
    treasury_altered = Column(Boolean, default=False, nullable=False)
    platform_fee = Column(Integer, default=200, nullable=False)
    treasury_address = Column(String(58), default="RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5", nullable=False)
    gateway_address = Column(String(58), nullable=True)
    authorized_app_id = Column(Integer, nullable=True)
    hitm_enforced = Column(Boolean, default=False, nullable=False)


class AccountQuarantine(Base):
    __tablename__ = "account_quarantines"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    address = Column(String, index=True, nullable=False)
    reason = Column(String, nullable=False)
    details = Column(String, nullable=True)
    quarantined_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at = Column(DateTime, nullable=False)
    status = Column(String, default="active", nullable=False)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(String, nullable=True)


class SyncRecord(Base):
    __tablename__ = "sync_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bounty_id = Column(String, ForeignKey("bounties.bounty_id", ondelete="CASCADE"), nullable=False)
    triggered_by = Column(String, nullable=False)
    triggered_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    github_state = Column(String, nullable=False)
    action_taken = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)



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


class Evaluator(Base):
    __tablename__ = "evaluators"
    address = Column(String, primary_key=True, index=True)
    status = Column(String, default="active", nullable=False)
    registered_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DisputeEvaluator(Base):
    __tablename__ = "dispute_evaluators"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bounty_id = Column(String, ForeignKey("bounties.bounty_id", ondelete="CASCADE"), nullable=False)
    evaluator_address = Column(String, ForeignKey("evaluators.address", ondelete="CASCADE"), nullable=False)
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


# ─── Terms of Service (Legal #171) ──────────────────────────────

class UserTermsAcceptance(Base):
    """Records a wallet address accepting the current ToS version."""
    __tablename__ = "user_terms_acceptance"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    address = Column(String, ForeignKey("agents.address", ondelete="CASCADE"), nullable=False)
    terms_version = Column(String, nullable=False)
    accepted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    accepted_ip_hash = Column(String, nullable=True)
    user_agent_hash = Column(String, nullable=True)
    __table_args__ = (
        UniqueConstraint("address", "terms_version", name="uq_terms_address_version"),
    )


class TermsHistory(Base):
    """Historical snapshots of ToS versions."""
    __tablename__ = "terms_history"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(String, unique=True, nullable=False)
    text = Column(Text, nullable=False)
    sha256_hash = Column(String, unique=True, nullable=False)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    is_active = Column(Boolean, default=True)
    governing_law = Column(String, nullable=True)
    arbitration_clause = Column(String, nullable=True)


class UserBlacklist(Base):
    """Admin-controlled blacklist for addresses."""
    __tablename__ = "user_blacklist"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    address = Column(String, ForeignKey("agents.address", ondelete="CASCADE"), unique=True, nullable=False)
    reason = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    blacklisted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    blacklisted_by = Column(String, ForeignKey("agents.address", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String, default="active", nullable=False)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)


# ─── Cold-start support (Karma #175) ────────────────────────────

class CollateralDeposit(Base):
    """Records ALGO locked by a new agent as temporary reputation proxy."""
    __tablename__ = "collateral_deposits"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_address = Column(String, ForeignKey("agents.address", ondelete="CASCADE"), nullable=False)
    amount_microalgo = Column(BigInteger, nullable=False)
    bounty_id = Column(String, ForeignKey("bounties.bounty_id", ondelete="CASCADE"), nullable=True)
    status = Column(String, default="locked", nullable=False)
    # locked = held while bounty is active
    # slashed = lost due to bounty failure
    # released = returned after successful completion
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    released_at = Column(DateTime, nullable=True)


class Vouch(Base):
    """Elite agent co-signing a new agent's bounty with partial reputation risk."""
    __tablename__ = "vouches"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vouching_agent = Column(String, ForeignKey("agents.address", ondelete="CASCADE"), nullable=False)
    vouched_agent = Column(String, ForeignKey("agents.address", ondelete="CASCADE"), nullable=False)
    bounty_id = Column(String, ForeignKey("bounties.bounty_id", ondelete="SET NULL"), nullable=True)
    amount_at_stake = Column(BigInteger, default=0)       # reputation capital at risk
    status = Column(String, default="active", nullable=False)
    # active, resolved, slashed, expired
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint("vouching_agent", "vouched_agent", "bounty_id", name="uq_vouch_triple"),
    )


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
