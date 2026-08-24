import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from gateway.main import app
from gateway.database import Base, Bounty, Agent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from gateway.dependencies import get_db
from gateway.auth import get_current_user

engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_worker():
    return "WORKER_ADDR"

def override_other():
    return "OTHER_ADDR"

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    worker = Agent(address="WORKER_ADDR", karma=50)
    other = Agent(address="OTHER_ADDR", karma=50)
    bounty = Bounty(
        bounty_id="ALGO-TEST-SYNC",
        creator="OTHER_ADDR",
        worker="WORKER_ADDR",
        status="submitted",
        amount=1000,
        repo_url="https://github.com/test/repo",
        payout_ready=False
    )
    db.add(worker)
    db.add(other)
    db.add(bounty)
    db.commit()
    db.close()

@pytest.mark.asyncio
async def test_sync_github_detects_merged_pr():
    app.dependency_overrides[get_current_user] = override_worker
    
    mock_res = {"state": "merged", "sha": "commit_sha_123", "event_id": "pr_1"}
    with patch("gateway.github.check_github_contribution_state", new=AsyncMock(return_value=mock_res)):
        res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/sync-github")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "synced"
        assert data["payout_ready"] == True

@pytest.mark.asyncio
async def test_sync_github_idempotent():
    app.dependency_overrides[get_current_user] = override_worker
    
    mock_res = {"state": "merged", "sha": "commit_sha_123", "event_id": "pr_1"}
    with patch("gateway.github.check_github_contribution_state", new=AsyncMock(return_value=mock_res)):
        res1 = client.post("/api/v1/bounties/ALGO-TEST-SYNC/sync-github")
        assert res1.json()["status"] == "synced"
        
        res2 = client.post("/api/v1/bounties/ALGO-TEST-SYNC/sync-github")
        assert res2.json()["status"] == "already_processed"

def test_claim_payout_requires_payout_ready():
    app.dependency_overrides[get_current_user] = override_worker
    res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/claim-payout")
    assert res.status_code == 409
    assert "Payout is not ready" in res.json()["detail"]

def test_claim_payout_worker_only():
    app.dependency_overrides[get_current_user] = override_other
    
    # Manually mark payout_ready in DB
    db = TestingSessionLocal()
    b = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-TEST-SYNC").first()
    b.payout_ready = True
    db.commit()
    db.close()
    
    res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/claim-payout")
    assert res.status_code == 403
    assert "Only the assigned worker" in res.json()["detail"]

def test_claim_payout_success():
    app.dependency_overrides[get_current_user] = override_worker
    
    db = TestingSessionLocal()
    b = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-TEST-SYNC").first()
    b.payout_ready = True
    db.commit()
    db.close()
    
    with patch("gateway.algod_client.release_trustless", return_value={"success": True, "tx_id": "MOCK_TX_999"}):
        res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/claim-payout")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "payout_complete"
        assert data["tx_id"] == "MOCK_TX_999"
