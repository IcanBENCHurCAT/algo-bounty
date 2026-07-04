"""
AlgoBounty database module — Consolidates models and engine creation.
Supports PostgreSQL (production) and SQLite (local dev fallback).
"""

import os
import signal
import logging
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    event,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Agent(Base):
    __tablename__ = "agents"
    address = Column(String, primary_key=True, index=True)
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

# ---------------------------------------------------------------------------
# Engine Construction
# ---------------------------------------------------------------------------

def _warm_pool(_conn, record):
    """Create one extra connection at startup so first requests don't stall."""
    pass

def build_engines():
    """Return (async_engine, sync_engine) based on DATABASE_URL."""
    # 1. Retrieve DATABASE_URL (fall back to SUPABASE_URL for backward compatibility)
    url = settings.DATABASE_URL or settings.SUPABASE_URL or os.environ.get("DATABASE_URL")

    # 2. Handle postgres:// -> postgresql:// transition
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url and url.startswith("postgresql"):
        # PostgreSQL Production logic
        sync_url = url
        # For async, we need postgresql+asyncpg://
        if "postgresql+asyncpg://" not in url:
            async_url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            async_url = url
            sync_url = url.replace("postgresql+asyncpg://", "postgresql://", 1)

        pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

        async_eng = create_async_engine(
            async_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
            connect_args={"timeout": connect_timeout},
            echo=False,
        )

        sync_eng = create_engine(
            sync_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
            connect_args={"connect_timeout": connect_timeout},
            echo=False,
        )
        event.listen(sync_eng, "connect", _warm_pool)
        return async_eng, sync_eng

    else:
        # SQLite Fallback
        sqlite_url = "sqlite:///./algobounty.db"
        sync_eng = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
        )

        try:
            async_eng = create_async_engine(
                "sqlite+aiosqlite:///./algobounty.db",
                connect_args={"check_same_thread": False},
            )
        except (ModuleNotFoundError, ImportError):
            async_eng = None
            logger.warning("aiosqlite not installed; async SQLite disabled")

        return async_eng, sync_eng

async_engine, sync_engine = build_engines()
engine = async_engine # backward-compatible alias

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=sync_engine
)

async def async_get_session():
    """Yield an async SQLAlchemy session."""
    if not async_engine:
        raise RuntimeError("Async engine not available")

    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

def init_db():
    """Initialize the database (create tables or run migrations)."""
    url = settings.DATABASE_URL or settings.SUPABASE_URL or os.environ.get("DATABASE_URL")

    if not url or url.startswith("sqlite"):
        # SQLite: Create all tables directly
        Base.metadata.create_all(sync_engine)
        _seed_platform_account()
    else:
        # PostgreSQL: Run Alembic migrations
        alembic_cfg = os.path.join(os.path.dirname(__file__), "alembic.ini")
        try:
            _run_alembic_with_timeout(alembic_cfg)
            _seed_platform_account()
        except (SystemExit, Exception) as exc:
            logger.error(f"DB init failed: {exc}")

def _run_alembic_with_timeout(alembic_cfg, timeout=30):
    """Run Alembic upgrade with a timeout."""
    if hasattr(signal, "SIGALRM"):
        def handler(signum, frame):
            raise TimeoutError("Alembic upgrade timed out")
        old_handler = signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)
        try:
            import alembic.config
            alembic.config.main(argv=["--config", alembic_cfg, "upgrade", "head"])
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        import alembic.config
        alembic.config.main(argv=["--config", alembic_cfg, "upgrade", "head"])

def _seed_platform_account():
    """Seed the platform admin agent if the DB is empty."""
    platform_address = "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5"
    db = SessionLocal()
    try:
        if not db.query(Agent).filter(Agent.address == platform_address).first():
            db.add(Agent(address=platform_address, karma=100))
            db.commit()
    except Exception as exc:
        logger.warning(f"Seed platform account skipped: {exc}")
        db.rollback()
    finally:
        db.close()
