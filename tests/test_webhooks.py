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
                          headers={"Content-Type": "application/json", "X-GitHub-Event": "issues", "X-Hub-Signature-256": "sha256=invalid"})
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

def test_github_webhook_endpoint_invalid_json(client):
    with patch("gateway.routers.webhooks.validate_webhook", return_value=(True, "")):
        res = client.post("/webhooks/github",
                          content=b"invalid_json_garbage",
                          headers={"Content-Type": "application/json", "X-GitHub-Event": "issues"})
        assert res.status_code == 400
        assert "Invalid JSON payload" in res.json()["reason"]

def test_github_webhook_events_dispatch(client, db_session):
    # Mock handlers
    with patch("gateway.routers.webhooks.validate_webhook", return_value=(True, "")), \
         patch("gateway.routers.webhooks.handle_issue_event") as mock_issue, \
         patch("gateway.routers.webhooks.handle_pr_event") as mock_pr:
         
        # 1. issues event
        res = client.post("/webhooks/github", json={"action": "opened"}, headers={"X-GitHub-Event": "issues"})
        assert res.status_code == 200
        mock_issue.assert_called_once()
        mock_issue.reset_mock()
        
        # 2. pull_request event
        res = client.post("/webhooks/github", json={"action": "opened"}, headers={"X-GitHub-Event": "pull_request"})
        assert res.status_code == 200
        mock_pr.assert_called_once()
        mock_pr.reset_mock()
        
        # 3. issue_comment event
        res = client.post("/webhooks/github", json={"action": "created"}, headers={"X-GitHub-Event": "issue_comment"})
        assert res.status_code == 200
        mock_issue.assert_called_once()
        mock_issue.reset_mock()
        
        # 4. pull_request_review event
        res = client.post("/webhooks/github", json={"action": "submitted"}, headers={"X-GitHub-Event": "pull_request_review"})
        assert res.status_code == 200
        mock_pr.assert_called_once()

