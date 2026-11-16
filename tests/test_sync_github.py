import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from gateway.main import app
from gateway.database import Base, Bounty, Agent, AccountQuarantine, GitHubPR
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from gateway.dependencies import get_db
from gateway.auth import get_current_user
from tests.conftest import override_get_db as default_override_get_db

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
    yield
    app.dependency_overrides[get_db] = default_override_get_db
    app.dependency_overrides.pop(get_current_user, None)

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

def test_sync_github_rejects_uninvolved_user():
    app.dependency_overrides[get_current_user] = lambda: "STRANGER_ADDR"
    res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/sync-github")
    assert res.status_code == 403
    assert "Only the assigned worker or bounty creator" in res.json()["detail"]

def test_claim_payout_rejects_unclaimed_bounty():
    app.dependency_overrides[get_current_user] = lambda: "STRANGER_ADDR"

    db = TestingSessionLocal()
    b = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-TEST-SYNC").first()
    b.worker = None
    b.payout_ready = True
    db.commit()
    db.close()

    res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/claim-payout")
    assert res.status_code == 403
    assert "Only the assigned worker" in res.json()["detail"]


def test_claim_payout_and_sync_reject_disputed_or_rejected_bounty():
    app.dependency_overrides[get_current_user] = override_worker

    for blocked_status in ("disputed", "rejected", "open"):
        db = TestingSessionLocal()
        b = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-TEST-SYNC").first()
        b.status = blocked_status
        b.payout_ready = True
        db.commit()
        db.close()

        sync_res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/sync-github")
        assert sync_res.status_code == 409
        assert blocked_status in sync_res.json()["detail"]

        payout_res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/claim-payout")
        assert payout_res.status_code == 409
        assert blocked_status in payout_res.json()["detail"]


def test_claim_payout_and_sync_reject_quarantined_worker():
    app.dependency_overrides[get_current_user] = override_worker

    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)
    db.add(
        AccountQuarantine(
            address="WORKER_ADDR",
            reason="Suspicious post-refund merge activity",
            quarantined_at=now,
            expires_at=now + timedelta(hours=24),
            status="active",
        )
    )
    b = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-TEST-SYNC").first()
    b.payout_ready = True
    db.commit()
    db.close()

    sync_res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/sync-github")
    assert sync_res.status_code == 403
    assert "quarantined" in sync_res.json()["detail"].lower()

    payout_res = client.post("/api/v1/bounties/ALGO-TEST-SYNC/claim-payout")
    assert payout_res.status_code == 403
    assert "quarantined" in payout_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_check_github_contribution_state_rejects_unauthorized_pr_author():
    from gateway.github import check_github_contribution_state

    db = TestingSessionLocal()
    worker = db.query(Agent).filter(Agent.address == "WORKER_ADDR").first()
    worker.github_username = "legit-worker"
    db.add(
        GitHubPR(
            pr_number=42,
            repo_url="https://github.com/test/repo",
            bounty_id="ALGO-TEST-SYNC",
            state="closed",
            author="attacker-user",
        )
    )
    db.commit()
    bounty = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-TEST-SYNC").first()

    spoofed_pr_resp = MagicMock(status_code=200)
    spoofed_pr_resp.json.return_value = {
        "number": 42,
        "merged": True,
        "merge_commit_sha": "deadbeef",
        "user": {"login": "attacker-user"},
    }
    closed_list_resp = MagicMock(status_code=200)
    closed_list_resp.json.return_value = [
        {
            "number": 99,
            "title": "Fix typo ALGO-TEST-SYNC",
            "body": "",
            "merged_at": "2026-11-16T00:00:00Z",
            "merge_commit_sha": "cafebabe",
            "user": {"login": "attacker-user"},
        }
    ]

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=[spoofed_pr_resp, closed_list_resp])

    with patch("gateway.github.httpx.AsyncClient", return_value=mock_client):
        result = await check_github_contribution_state(bounty, db)

    assert result["state"] == "open"
    db.close()
