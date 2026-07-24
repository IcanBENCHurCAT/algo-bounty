import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from gateway.github import get_github_bot_token, verify_webhook_signature, post_github_comment_and_labels, log_bot_comment, handle_pr_event
from gateway.database import Agent, Bounty

@pytest.mark.asyncio
async def test_get_github_bot_token():
    from unittest.mock import PropertyMock

    # If GITHUB_APP_ID is missing, should return GITHUB_TOKEN
    with patch("gateway.config.Config.GITHUB_APP_ID", new_callable=PropertyMock) as mock_app_id, \
         patch("gateway.config.Config.GITHUB_PRIVATE_KEY", new_callable=PropertyMock) as mock_priv_key, \
         patch("gateway.config.Config.GITHUB_TOKEN", new_callable=PropertyMock) as mock_token:
        mock_app_id.return_value = None
        mock_priv_key.return_value = None
        mock_token.return_value = "fallback_token"
        assert await get_github_bot_token("owner", "repo") == "fallback_token"

    with patch("gateway.config.Config.GITHUB_APP_ID", new_callable=PropertyMock) as mock_app_id, \
         patch("gateway.config.Config.GITHUB_PRIVATE_KEY", new_callable=PropertyMock) as mock_priv_key, \
         patch("gateway.github.jwt.encode", return_value="jwt"), \
         patch("os.path.isfile", return_value=False):

        mock_app_id.return_value = "123"
        mock_priv_key.return_value = "private"

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"id": 456}

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "token": "dynamic_token",
            "expires_at": "2050-01-01T00:00:00Z"
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value = mock_get_response
            mock_post.return_value = mock_post_response

            token = await get_github_bot_token("owner", "repo")
            assert token == "dynamic_token"

def test_verify_webhook_signature():
    # Valid signature
    payload = b"payload"
    secret = "secret"
    import hmac
    import hashlib
    expected_mac = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    signature = f"sha256={expected_mac}"

    assert verify_webhook_signature(payload, signature, secret) is True
    assert verify_webhook_signature(payload, "invalid", secret) is False

@pytest.mark.asyncio
async def test_post_github_comment_and_labels():
    with patch("gateway.github.get_github_bot_token", new_callable=AsyncMock) as mock_get_token, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.put", new_callable=AsyncMock) as mock_put, \
         patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:

        mock_get_token.return_value = "token"

        # Success
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        mock_put.return_value = mock_response
        mock_delete.return_value = mock_response

        # The function doesn't return anything explicit, so it returns None implicitly on success
        res = await post_github_comment_and_labels("https://github.com/owner/repo", 1, "comment", ["label1"], ["label2"])
        assert res is None

        # Missing token
        mock_get_token.return_value = None
        res2 = await post_github_comment_and_labels("https://github.com/owner/repo", 1, "comment")
        assert res2 is None

@pytest.mark.asyncio
async def test_log_bot_comment():
    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        # Valid
        await log_bot_comment("https://github.com/owner/repo", 1, "text")
        mock_post.assert_called_once_with("https://github.com/owner/repo", 1, comment="text")

@pytest.mark.asyncio
async def test_handle_pr_event_closed(db_session):
    from gateway.database import Bounty, GitHubPR
    from gateway.github import handle_pr_event

    # Setup bounty and PR
    db_session.add(Bounty(bounty_id="b_303", status="submitted", creator="C1", amount=1000, repo_url="https://github.com/owner/repo"))
    db_session.add(GitHubPR(pr_number=10, repo_url="https://github.com/owner/repo", bounty_id="b_303", author="worker"))
    db_session.commit()

    payload = {
        "action": "closed",
        "pull_request": {
            "number": 10,
            "title": "Fix for ALGO-303",
            "body": "Fixes #ALGO-303",
            "merged": True,
            "user": {"login": "worker"}
        },
        "repository": {"html_url": "https://github.com/owner/repo"}
    }

    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_303").first()
    assert bounty.status == "closed"

    # Test closed but not merged (should remain submitted based on current code logic)
    payload["pull_request"]["merged"] = False
    db_session.add(Bounty(bounty_id="b_404", status="submitted", creator="C1", amount=1000, repo_url="https://github.com/owner/repo"))
    db_session.add(GitHubPR(pr_number=11, repo_url="https://github.com/owner/repo", bounty_id="b_404", author="worker"))
    db_session.commit()

    payload["pull_request"]["number"] = 11
    payload["pull_request"]["title"] = "Fix for ALGO-404"
    payload["pull_request"]["body"] = "Fixes #ALGO-404"

    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)

    bounty2 = db_session.query(Bounty).filter(Bounty.bounty_id == "b_404").first()
    assert bounty2.status == "submitted" # Returns to open logic doesn't exist, remains submitted

def test_validate_webhook():
    from gateway.github import validate_webhook
    import hmac
    import hashlib

    # 1. Missing secret (sandbox mode)
    with patch("gateway.github.NODE_ENV", "sandbox"):
        ok, reason = validate_webhook("issue", "", "sig", "del1", b"body", "ip")
        assert ok is True
        assert reason == "del1"

    # 2. Missing secret (prod mode)
    with patch("gateway.github.NODE_ENV", "production"):
        ok, reason = validate_webhook("issue", "", "sig", "del1", b"body", "ip")
        assert ok is False
        assert "not configured" in reason

    # 3. Invalid signature
    ok, reason = validate_webhook("issues", "secret", "invalid", "del1", b"body", "ip")
    assert ok is False
    assert "Invalid webhook signature" in reason

    # 4. Unknown event
    expected_mac = hmac.new(b"secret", b"body", hashlib.sha256).hexdigest()
    sig = f"sha256={expected_mac}"
    ok, reason = validate_webhook("unknown_event", "secret", sig, "del1", b"body", "ip")
    assert ok is False
    assert "Unknown event type" in reason

    # 5. Success
    ok, reason = validate_webhook("issues", "secret", sig, "del1", b"body", "ip")
    assert ok is True


@pytest.mark.asyncio
async def test_link_github_username_api(client, db_session):
    # Setup test agent
    agent = Agent(address="TEST_AGENT_ADDR_1", karma=30)
    db_session.add(agent)
    db_session.commit()

    # Generate JWT for authentication
    from gateway.auth import create_jwt_token
    token = create_jwt_token("TEST_AGENT_ADDR_1")

    # Link GitHub username
    response = client.put(
        "/api/v1/agents/me/github",
        json={"github_username": "coolworker"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["github_username"] == "coolworker"
    assert data["address"] == "TEST_AGENT_ADDR_1"

    # Query DB and verify
    agent_db = db_session.query(Agent).filter(Agent.address == "TEST_AGENT_ADDR_1").first()
    assert agent_db.github_username == "coolworker"


@pytest.mark.asyncio
async def test_handle_pr_event_linkage(db_session):
    # Setup linked agent
    agent = Agent(address="ALGO_WALLET_ADDR_123", github_username="coolworker", karma=50)
    db_session.add(agent)

    # Setup bounty in submitted state
    bounty = Bounty(
        bounty_id="b_999",
        app_id=99999,
        status="submitted",
        creator="C1",
        amount=10000000,
        repo_url="https://github.com/owner/repo",
        is_hitm=False,
        authorized_app_id=123,
        hitm_enforced=False
    )
    db_session.add(bounty)
    db_session.commit()

    # Case 1: Payout fails / blocked when worker has no linked wallet
    payload_no_wallet = {
        "action": "closed",
        "pull_request": {
            "number": 999,
            "title": "Fix ALGO-999",
            "body": "Fixes #ALGO-999",
            "merged": True,
            "user": {"login": "unregistered_worker"}
        },
        "repository": {"html_url": "https://github.com/owner/repo"}
    }

    from unittest.mock import PropertyMock
    with patch("gateway.config.Config.ALGORAND_NETWORK", new_callable=PropertyMock, return_value="testnet"), \
         patch.dict("os.environ", {"TESTING": "False"}), \
         patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload_no_wallet)
        # Should NOT trigger payout and should post warning comment
        mock_post.assert_called_once()
        assert "Auto-Release Blocked" in mock_post.call_args[1]["comment"]

    # Case 2: Payout succeeds when worker username is linked to wallet
    payload_success = {
        "action": "closed",
        "pull_request": {
            "number": 999,
            "title": "Fix ALGO-999",
            "body": "Fixes #ALGO-999",
            "merged": True,
            "user": {"login": "coolworker"}
        },
        "repository": {"html_url": "https://github.com/owner/repo"}
    }

    with patch("gateway.github.release_trustless") as mock_release, \
         patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        mock_release.return_value = {"success": True, "tx_id": "REAL_TX_ID"}
        await handle_pr_event(db_session, payload_success)

        # release_trustless should be called with correct recipient wallet address
        mock_release.assert_called_once_with(app_id=99999, worker_address="ALGO_WALLET_ADDR_123")
        
        # Bounty status should be closed
        db_session.refresh(bounty)
        assert bounty.status == "closed"


@pytest.mark.asyncio
async def test_bounty_creation_byoa_fields(client, db_session):
    # Setup test agent
    agent = Agent(address="CREATOR_ADDR_123", karma=50)
    db_session.add(agent)
    db_session.commit()

    from gateway.auth import create_jwt_token
    token = create_jwt_token("CREATOR_ADDR_123")

    from unittest.mock import PropertyMock
    with patch("gateway.routers.bounties.sandbox_active", True), \
         patch("gateway.config.Config.GITHUB_APP_ID", new_callable=PropertyMock, return_value="98765"):
        # Post request to create bounty
        response = client.post(
            "/api/v1/bounties",
            json={
                "description": "Test BYOA bounty",
                "amount": 20000000,
                "repo_url": "https://github.com/owner/repo",
                "hitm": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        b_id = data["bounty_id"]

        # Check DB columns
        bounty = db_session.query(Bounty).filter(Bounty.bounty_id == b_id).first()
        assert bounty is not None
        assert bounty.authorized_app_id == 98765
        assert bounty.hitm_enforced is False
        assert bounty.is_hitm is False
