import os

# Set environment before importing gateway modules
os.environ["ALGORAND_NETWORK"] = "sandbox"
import pytest

# Set dummy secret for tests BEFORE importing gateway modules
os.environ["SECRET_KEY"] = "test_dummy_secret_key_at_least_32_characters_long"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gateway.main import app, get_db
from gateway.database import Base, Agent, Bounty

# Setup Test Database (in-memory SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_algobounty.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Seed default agents
    creator = Agent(address="RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5", karma=50)
    worker = Agent(address="RTCedWorkerAddress555abc123999testwork", karma=30)
    db.add(creator)
    db.add(worker)
    db.commit()
    db.close()
    
    yield
    
    # Teardown
    Base.metadata.drop_all(bind=engine)

from unittest.mock import patch

def get_auth_token(address: str) -> str:
    # 1. Request challenge
    res = client.post("/api/v1/auth/request", json={"address": address})
    assert res.status_code == 200
    challenge = res.json()["challenge"]
    
    # 2. Verify with mock signature
    # We mock util.verify_bytes to return True for tests
    with patch("gateway.auth.util.verify_bytes", return_value=True):
        verify_res = client.post("/api/v1/auth/verify", json={
            "address": address,
            "signature": "fake_signature",
            "challenge": challenge
        })
        assert verify_res.status_code == 200
        return verify_res.json()["jwt"]

# Test cases

def test_auth_request_verify():
    addr = "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5"
    token = get_auth_token(addr)
    assert token is not None

def test_create_and_list_bounties():
    creator_addr = "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5"
    token = get_auth_token(creator_addr)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Post a bounty
    bounty_payload = {
        "description": "Fix memory leaks in surveillance-rpg asset loader",
        "amount": 50000000, # 50 ALGO
        "asset_id": 0,
        "hitm": True,
        "repo_url": "https://github.com/vantage-labs/surveillance-rpg",
        "karma_requirement": 10
    }
    
    create_res = client.post("/api/v1/bounties", json=bounty_payload, headers=headers)
    assert create_res.status_code == 200
    data = create_res.json()
    assert data["status"] == "open"
    bounty_id = data["bounty_id"]
    
    # List bounties and check if it's there
    list_res = client.get("/api/v1/bounties")
    assert list_res.status_code == 200
    bounties = list_res.json()["bounties"]
    assert len(bounties) > 0
    assert bounties[0]["bounty_id"] == bounty_id
    assert bounties[0]["amount"] == 50000000

def test_bounty_claim_submit_approve_flow():
    creator_addr = "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5"
    worker_addr = "RTCedWorkerAddress555abc123999testwork"
    
    creator_token = get_auth_token(creator_addr)
    worker_token = get_auth_token(worker_addr)
    
    # 1. Creator creates bounty
    bounty_payload = {
        "description": "Create automated setup script for vintage miner",
        "amount": 25000000,
        "repo_url": "https://github.com/vantage-labs/vintage-miner",
        "hitm": False
    }
    res = client.post("/api/v1/bounties", json=bounty_payload, headers={"Authorization": f"Bearer {creator_token}"})
    bounty_id = res.json()["bounty_id"]
    
    # 2. Worker claims bounty
    claim_res = client.post(f"/api/v1/bounties/{bounty_id}/claim", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})
    assert claim_res.status_code == 200
    assert claim_res.json()["status"] == "claimed"
    
    # 3. Worker submits PR solution
    submit_res = client.post(
        f"/api/v1/bounties/{bounty_id}/submit", 
        json={
            "pr_url": "https://github.com/vantage-labs/vintage-miner/pull/4",
            "proof_data": {"type": "code"},
            "signed_txn": ""
        }, 
        headers={"Authorization": f"Bearer {worker_token}"}
    )
    assert submit_res.status_code == 200
    
    # 4. Creator approves solution
    approve_res = client.post(f"/api/v1/bounties/{bounty_id}/approve", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {creator_token}"})
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "closed"
    assert approve_res.json()["payout_type"] == "PAYOUT"

def test_github_webhook_issue_and_pr_sync():
    # 1. Trigger GitHub webhook: Issue Created (which has title and label for bounty)
    issue_payload = {
        "action": "opened",
        "issue": {
            "number": 102,
            "title": "[ALGO-BOUNTY] Integrate telemetry metrics indexer",
            "body": "bounty: 15000000 microALGO. Requires custom indexer stats logging.",
            "labels": [{"name": "bounty"}],
            "user": {"login": "GarretDev"}
        },
        "repository": {
            "html_url": "https://github.com/vantage-labs/telemetry-indexer"
        }
    }
    
    webhook_res = client.post(
        "/webhooks/github", 
        json=issue_payload, 
        headers={"X-GitHub-Event": "issues"}
    )
    assert webhook_res.status_code == 200
    assert webhook_res.json()["status"] == "event_processed"
    
    # Verify the bounty was created in the database (pending_payment state)
    bounty_res = client.get("/api/v1/bounties?status=pending_payment")
    assert bounty_res.status_code == 200
    bounties = bounty_res.json()["bounties"]
    assert len(bounties) == 1
    bounty = bounties[0]
    assert bounty["bounty_id"] == "b_102"
    assert bounty["amount"] == 15000000
    
    # Simulate payment completion and activate bounty (admin/gateway action)
    db = TestingSessionLocal()
    b = db.query(Bounty).filter(Bounty.bounty_id == "b_102").first()
    b.status = "open"
    db.commit()
    db.close()
    
    # 2. Trigger GitHub webhook: PR Opened referring to #ALGO-102
    pr_payload = {
        "action": "opened",
        "pull_request": {
            "number": 14,
            "title": "Fix indexer logging (#ALGO-102)",
            "body": "Linked to ALGO-102 task",
            "state": "open",
            "user": {"login": "agent_coder"}
        },
        "repository": {
            "html_url": "https://github.com/vantage-labs/telemetry-indexer"
        }
    }
    
    pr_webhook_res = client.post(
        "/webhooks/github",
        json=pr_payload,
        headers={"X-GitHub-Event": "pull_request"}
    )
    assert pr_webhook_res.status_code == 200
    
    # Verify bounty state transitioned to claimed & linked to the worker
    detail_res = client.get("/api/v1/bounties/b_102")
    assert detail_res.status_code == 200
    assert detail_res.json()["status"] == "claimed"
    assert detail_res.json()["worker"] == "agent_coder"
