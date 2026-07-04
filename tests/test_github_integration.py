import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from gateway.database import Bounty, GitHubPR
from gateway.github import extract_bounty_ids, handle_issue_event, handle_pr_event

def test_extract_bounty_ids():
    body = "Fixes ALGO-123 and also #ALGO-456. Duplicate ALGO-123"
    ids = extract_bounty_ids(body)
    assert "123" in ids
    assert "456" in ids
    assert len(ids) == 2

@pytest.mark.asyncio
async def test_oidc_verify_endpoint_success(client):
    mock_payload = {"repository": "owner/repo", "workflow": "test-wf"}

    with patch("gateway.routers.oidc.verify_github_oidc_token", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = mock_payload

        response = client.post("/api/v1/oidc/verify", json={
            "token": "fake_token",
            "expected_repo": "owner/repo"
        })

        assert response.status_code == 200
        assert response.json()["status"] == "verified"
        assert response.json()["payload"] == mock_payload

@pytest.mark.asyncio
async def test_handle_issue_event(db_session):
    payload = {
        "action": "opened",
        "issue": {
            "number": 101,
            "title": "[ALGO-BOUNTY] Test Bounty",
            "body": "bounty: 5000000",
            "labels": [{"name": "bounty"}],
            "user": {"login": "testuser"}
        },
        "repository": {
            "html_url": "https://github.com/owner/repo"
        }
    }

    with patch("gateway.github.get_github_bot_token", return_value=AsyncMock(return_value="fake_token")), \
         patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        await handle_issue_event(db_session, payload)

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_101").first()
    assert bounty is not None
    assert bounty.amount == 5000000
    assert bounty.status == "pending_payment"

@pytest.mark.asyncio
async def test_handle_pr_event_claim(db_session):
    # Create bounty
    db_session.add(Bounty(bounty_id="b_202", status="open", creator="C1", amount=1000, repo_url="https://github.com/owner/repo"))
    db_session.commit()

    payload = {
        "action": "opened",
        "pull_request": {
            "number": 5,
            "title": "Fix for ALGO-202",
            "body": "Linked to #ALGO-202",
            "state": "open",
            "user": {"login": "worker1"}
        },
        "repository": {
            "html_url": "https://github.com/owner/repo"
        }
    }

    with patch("gateway.github.get_github_bot_token", return_value=AsyncMock(return_value="fake_token")), \
         patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        await handle_pr_event(db_session, payload)

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_202").first()
    assert bounty.status == "claimed"
    assert bounty.worker == "worker1"

    pr = db_session.query(GitHubPR).filter(GitHubPR.pr_number == 5).first()
    assert pr is not None
    assert pr.bounty_id == "b_202"
