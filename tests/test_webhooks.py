import pytest
from unittest.mock import patch, MagicMock
from gateway.github import verify_webhook_signature, handle_pr_event
from gateway.database import Bounty, Agent

def test_verify_webhook_signature():
    secret = "test_secret"
    payload = b'{"action": "opened"}'
    # Compute expected signature
    import hmac
    import hashlib
    expected_hex = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    signature = f"sha256={expected_hex}"

    assert verify_webhook_signature(payload, signature, secret) is True
    assert verify_webhook_signature(payload, "sha256=wrong", secret) is False
    assert verify_webhook_signature(payload, signature, "wrong_secret") is False

def test_github_webhook_endpoint_invalid_sig(client):
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": "secret", "NODE_ENV": "production"}):
        res = client.post("/webhooks/github",
                          content=b"payload",
                          headers={"X-GitHub-Event": "issues", "X-Hub-Signature-256": "sha256=invalid"})
        assert res.status_code == 403

def test_handle_pr_merged_trustless(db_session):
    # Create bounty in trustless mode (is_hitm=False)
    # Status must be 'claimed' or 'submitted' for merged PR to trigger payout
    db_session.add(Bounty(bounty_id="b_123", status="submitted", creator="C1", worker="W1", amount=1000, is_hitm=False, repo_url="https://github.com/owner/repo"))
    db_session.add(Agent(address="W1", karma=30))
    db_session.commit()

    payload = {
        "action": "closed",
        "pull_request": {
            "number": 10,
            "title": "Fix ALGO-123",
            "body": "Fixes ALGO-123",
            "merged": True,
            "state": "closed",
            "user": {"login": "W1"}
        },
        "repository": {
            "html_url": "https://github.com/owner/repo"
        }
    }

    with patch("gateway.github.get_github_bot_token", return_value="fake_token"), \
         patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        handle_pr_event(db_session, payload)

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_123").first()
    assert bounty.status == "closed"
    assert bounty.payout_type == "PAYOUT"

    worker = db_session.query(Agent).filter(Agent.address == "W1").first()
    assert worker.karma == 35 # 30 + 5
