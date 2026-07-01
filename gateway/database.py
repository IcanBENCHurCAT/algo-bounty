import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./algobounty.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Agent(Base):
    __tablename__ = "agents"
    address = Column(String, primary_key=True, index=True)
    karma = Column(Integer, default=25)  # Novice starts with 25 karma
    completed_bounties = Column(Integer, default=0)
    disputes_lost = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Bounty(Base):
    __tablename__ = "bounties"
    bounty_id = Column(String, primary_key=True, index=True)
    app_id = Column(Integer, unique=True, index=True, nullable=True)  # Algorand App ID
    status = Column(String, default="open")  # open, claimed, submitted, rejected, disputed, closed
    creator = Column(String, index=True)
    worker = Column(String, index=True, nullable=True)
    amount = Column(Integer)  # microALGO or ASA units
    asset_id = Column(Integer, default=0)  # 0 for ALGO native
    is_hitm = Column(Boolean, default=False)
    description = Column(String)
    repo_url = Column(String, index=True)
    karma_requirement = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline_round = Column(Integer, nullable=True)
    hitm_review_days = Column(Integer, default=7)
    rejection_count = Column(Integer, default=0)
    payout_type = Column(String, nullable=True)  # PAYOUT, REFUND, SPLIT

class GitHubPR(Base):
    __tablename__ = "github_prs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pr_number = Column(Integer, index=True)
    repo_url = Column(String, index=True)
    bounty_id = Column(String, ForeignKey("bounties.bounty_id"))
    state = Column(String, default="open")  # open, merged, closed
    author = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipient = Column(String, index=True)  # Wallet address
    message = Column(String)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Seed default agents/mediators if not present
    db = SessionLocal()
    try:
        # Check if platform account is seeded
        platform_address = "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5"
        if not db.query(Agent).filter(Agent.address == platform_address).first():
            platform_agent = Agent(address=platform_address, karma=100)
            db.add(platform_agent)
            db.commit()
    finally:
        db.close()
