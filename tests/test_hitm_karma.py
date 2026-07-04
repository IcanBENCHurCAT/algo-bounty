import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gateway.database import Base, Bounty, Agent, Notification
from gateway.routers.bounties import create_bounty, approve_work, reject_work
from gateway.schemas import BountyCreate, WorkApprove, WorkReject
from unittest.mock import MagicMock, patch
import base64
import asyncio

# In-memory SQLite for testing karma logic
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    # Seed agents
    session.add(Agent(address="creator_addr", karma=100))
    session.add(Agent(address="worker_addr", karma=100))
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_karma_on_create(db):
    body = BountyCreate(
        description="Test Bounty",
        amount=10,
        asset_id=0,
        hitm=True,
        repo_url="https://github.com/test/repo",
        karma_requirement=0,
        hitm_review_days=7
    )

    with patch("gateway.routers.bounties.get_algod_client"), \
         patch("gateway.routers.bounties.compile_escrow_contract"), \
         patch("gateway.routers.bounties.is_sandbox", return_value=True):
        create_bounty(body, db, "creator_addr")

    creator = db.query(Agent).filter(Agent.address == "creator_addr").first()
    assert creator.karma == 99  # -1 for creation

def test_karma_on_approve(db):
    bounty = Bounty(
        bounty_id="b_123",
        status="submitted",
        creator="creator_addr",
        worker="worker_addr",
        amount=10,
        is_hitm=True,
        repo_url="https://github.com/test/repo"
    )
    db.add(bounty)
    db.commit()

    body = WorkApprove(signed_txn=None)
    with patch("gateway.routers.bounties.send_signed_transaction"):
        approve_work("b_123", body, db, "creator_addr")

    worker = db.query(Agent).filter(Agent.address == "worker_addr").first()
    creator = db.query(Agent).filter(Agent.address == "creator_addr").first()

    assert worker.karma == 110  # +10
    assert creator.karma == 105  # +5

def test_karma_on_progressive_reject(db):
    bounty = Bounty(
        bounty_id="b_123",
        status="submitted",
        creator="creator_addr",
        worker="worker_addr",
        amount=10,
        rejection_count=0,
        repo_url="https://github.com/test/repo"
    )
    db.add(bounty)
    db.commit()

    body = WorkReject(reason="bad", signed_txn=None)
    with patch("gateway.routers.bounties.send_signed_transaction"):
        # 1st rejection
        reject_work("b_123", body, db, "creator_addr")
        worker = db.query(Agent).filter(Agent.address == "worker_addr").first()
        assert worker.karma == 99  # -1

        # 2nd rejection (simulating re-submission and re-rejection)
        bounty.status = "submitted"
        db.commit()
        reject_work("b_123", body, db, "creator_addr")
        assert worker.karma == 97  # 99 - 2 = 97

        # 3rd rejection
        bounty.status = "submitted"
        db.commit()
        reject_work("b_123", body, db, "creator_addr")
        assert worker.karma == 92  # 97 - 5 = 92

def test_indexer_auto_release(db):
    from gateway.worker import indexer_worker

    bounty = Bounty(
        bounty_id="b_hitm",
        app_id=1001,
        status="submitted",
        creator="creator_addr",
        worker="worker_addr",
        amount=10,
        is_hitm=True,
        repo_url="https://github.com/test/repo"
    )
    db.add(bounty)
    db.commit()

    # Mock fetch_app_logs to return auto_released_hitm log
    mock_logs = [{
        "round": 100,
        "logs": [base64.b64encode(b"auto_released_hitm").decode()]
    }]

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.SessionLocal", return_value=db), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):
        asyncio.run(indexer_worker())

    b = db.query(Bounty).filter(Bounty.bounty_id == "b_hitm").first()
    assert b.status == "closed"
    assert b.payout_type == "PAYOUT"

    worker = db.query(Agent).filter(Agent.address == "worker_addr").first()
    creator = db.query(Agent).filter(Agent.address == "creator_addr").first()
    assert worker.karma == 103  # +3
    assert creator.karma == 102  # +2

def test_indexer_dispute_timeout(db):
    from gateway.worker import indexer_worker

    bounty = Bounty(
        bounty_id="b_dispute",
        app_id=1002,
        status="disputed",
        creator="creator_addr",
        worker="worker_addr",
        amount=10,
        repo_url="https://github.com/test/repo"
    )
    db.add(bounty)
    db.commit()

    # Mock fetch_app_logs to return dispute_timeout_split log
    mock_logs = [{
        "round": 110,
        "logs": [base64.b64encode(b"dispute_timeout_split").decode()]
    }]

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.SessionLocal", return_value=db), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):
        asyncio.run(indexer_worker())

    b = db.query(Bounty).filter(Bounty.bounty_id == "b_dispute").first()
    assert b.status == "closed"
    assert b.payout_type == "SPLIT"

    worker = db.query(Agent).filter(Agent.address == "worker_addr").first()
    creator = db.query(Agent).filter(Agent.address == "creator_addr").first()
    assert worker.karma == 99  # -1
    assert creator.karma == 99  # -1

def test_indexer_claim_expired(db):
    from gateway.worker import indexer_worker

    bounty = Bounty(
        bounty_id="b_expired",
        app_id=1003,
        status="claimed",
        creator="creator_addr",
        worker="worker_addr",
        amount=10,
        repo_url="https://github.com/test/repo"
    )
    db.add(bounty)
    db.commit()

    # Mock fetch_app_logs to return claim_expired log
    mock_logs = [{
        "round": 120,
        "logs": [base64.b64encode(b"claim_expired").decode()]
    }]

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.SessionLocal", return_value=db), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):
        asyncio.run(indexer_worker())

    b = db.query(Bounty).filter(Bounty.bounty_id == "b_expired").first()
    assert b.status == "open"
    assert b.worker is None

    worker = db.query(Agent).filter(Agent.address == "worker_addr").first()
    assert worker.karma == 80  # -20
