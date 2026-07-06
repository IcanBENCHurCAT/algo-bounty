import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from gateway.github import get_github_bot_token, verify_webhook_signature, post_github_comment_and_labels, log_bot_comment

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
