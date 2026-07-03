import pytest
from unittest.mock import patch
from gateway.database import Agent, Bounty
from tests.conftest import get_auth_token



@pytest.fixture(autouse=True)
def reset_rate_limit():
    from gateway.rate_limiter import _request_log, _lock
    with _lock:
        _request_log.clear()

def test_claim_own_bounty(client, seeded_agents):
    token = get_auth_token(client, "CREATOR_ADDR")
    headers = {"Authorization": f"Bearer {token}"}

    # Create bounty
    bounty_payload = {
        "description": "Test Bounty",
        "amount": 10,
        "repo_url": "https://github.com/test/test",
        "hitm": False
    }
    res = client.post("/api/v1/bounties", json=bounty_payload, headers=headers)
    assert res.status_code == 200
    bounty_id = res.json()["bounty_id"]

    # Try to claim own bounty
    claim_res = client.post(f"/api/v1/bounties/{bounty_id}/claim", json={"signed_txn": ""}, headers=headers)
    assert claim_res.status_code == 400
    assert "Cannot claim your own bounty" in claim_res.json()["detail"]

def test_claim_insufficient_karma(client, seeded_agents):
    creator_token = get_auth_token(client, "CREATOR_ADDR")
    low_karma_token = get_auth_token(client, "LOW_KARMA_WORKER")

    # Create bounty with karma requirement 10
    bounty_payload = {
        "description": "Test Karma Bounty",
        "amount": 10,
        "repo_url": "https://github.com/test/test",
        "hitm": False,
        "karma_requirement": 10
    }
    res = client.post("/api/v1/bounties", json=bounty_payload, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 200
    bounty_id = res.json()["bounty_id"]

    # Try to claim with 5 karma
    claim_res = client.post(f"/api/v1/bounties/{bounty_id}/claim", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {low_karma_token}"})
    assert claim_res.status_code == 403
    assert "Insufficient karma" in claim_res.json()["detail"]

def test_unauthorized_approve(client, seeded_agents):
    creator_token = get_auth_token(client, "CREATOR_ADDR")
    worker_token = get_auth_token(client, "WORKER_ADDR")

    # Create and claim
    res = client.post("/api/v1/bounties", json={"description": "Test", "amount": 1, "repo_url": "https://github.com/test/test"}, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 200
    bounty_id = res.json()["bounty_id"]

    client.post(f"/api/v1/bounties/{bounty_id}/claim", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})
    client.post(f"/api/v1/bounties/{bounty_id}/submit", json={"pr_url": "https://github.com/test/test/pull/1", "proof_data": {}, "signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})

    # Worker tries to approve their own work
    approve_res = client.post(f"/api/v1/bounties/{bounty_id}/approve", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})
    assert approve_res.status_code == 403
    assert "Only creator can approve" in approve_res.json()["detail"]

def test_invalid_state_transition_approve(client, seeded_agents):
    token = get_auth_token(client, "CREATOR_ADDR")
    res = client.post("/api/v1/bounties", json={"description": "Test", "amount": 1, "repo_url": "https://github.com/test/test"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    bounty_id = res.json()["bounty_id"]

    # Approve while still "open"
    approve_res = client.post(f"/api/v1/bounties/{bounty_id}/approve", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {token}"})
    assert approve_res.status_code == 400
    assert "no work submitted" in approve_res.json()["detail"]

def test_rejection_karma_penalties(client, seeded_agents, db_session):
    creator_token = get_auth_token(client, "CREATOR_ADDR")
    worker_token = get_auth_token(client, "WORKER_ADDR")

    res = client.post("/api/v1/bounties", json={"description": "Test", "amount": 1, "repo_url": "https://github.com/test/test"}, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 200
    bounty_id = res.json()["bounty_id"]

    client.post(f"/api/v1/bounties/{bounty_id}/claim", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})

    # Rejection 1: -1 karma
    client.post(f"/api/v1/bounties/{bounty_id}/submit", json={"pr_url": "https://github.com/test/test/pull/1", "proof_data": {}, "signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})
    client.post(f"/api/v1/bounties/{bounty_id}/reject", json={"reason": "bad", "signed_txn": ""}, headers={"Authorization": f"Bearer {creator_token}"})

    worker = db_session.query(Agent).filter(Agent.address == "WORKER_ADDR").first()
    assert worker.karma == 29 # 30 - 1

    # Rejection 2: -2 karma
    client.post(f"/api/v1/bounties/{bounty_id}/submit", json={"pr_url": "https://github.com/test/test/pull/1", "proof_data": {}, "signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})
    client.post(f"/api/v1/bounties/{bounty_id}/reject", json={"reason": "bad again", "signed_txn": ""}, headers={"Authorization": f"Bearer {creator_token}"})

    db_session.refresh(worker)
    assert worker.karma == 27 # 29 - 2

    # Rejection 3: -5 karma
    client.post(f"/api/v1/bounties/{bounty_id}/submit", json={"pr_url": "https://github.com/test/test/pull/1", "proof_data": {}, "signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})
    client.post(f"/api/v1/bounties/{bounty_id}/reject", json={"reason": "bad again 3", "signed_txn": ""}, headers={"Authorization": f"Bearer {creator_token}"})

    db_session.refresh(worker)
    assert worker.karma == 22 # 27 - 5

def test_dispute_unauthorized(client, seeded_agents):
    creator_token = get_auth_token(client, "CREATOR_ADDR")
    worker_token = get_auth_token(client, "WORKER_ADDR")
    random_token = get_auth_token(client, "LOW_KARMA_WORKER")

    res = client.post("/api/v1/bounties", json={"description": "Test", "amount": 1, "repo_url": "https://github.com/test/test"}, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 200
    bounty_id = res.json()["bounty_id"]

    client.post(f"/api/v1/bounties/{bounty_id}/claim", json={"signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})
    client.post(f"/api/v1/bounties/{bounty_id}/submit", json={"pr_url": "https://github.com/test/test/pull/1", "proof_data": {}, "signed_txn": ""}, headers={"Authorization": f"Bearer {worker_token}"})

    # Random user tries to dispute
    dispute_res = client.post(f"/api/v1/bounties/{bounty_id}/dispute", json={"reason": "none", "signed_txn": ""}, headers={"Authorization": f"Bearer {random_token}"})
    assert dispute_res.status_code == 403
    assert "Only bounty participants" in dispute_res.json()["detail"]
