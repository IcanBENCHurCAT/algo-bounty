"""
Tests for Issue #169: PR Spoofing Verification and Worker Claim Isolation.

Verifies:
1. normalize_repo_url handles case, trailing slashes, and .git suffix correctly.
2. Webhook PR events from mismatched repo_url are rejected (no linking, claiming, or transitioning).
3. Webhook PR events with normalized matching repo_url succeed.
4. Worker claim isolation prevents unauthorized authors from transitioning or hijacking claimed bounties.
5. Worker claim isolation prevents unauthorized authors from receiving payouts on merged PRs.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from gateway.github import normalize_repo_url, is_worker_authorized, handle_pr_event
from gateway.database import Bounty, GitHubPR, Agent


def test_normalize_repo_url():
    """Verify repository URL normalization logic."""
    expected = "https://github.com/legit-org/legit-repo"
    assert normalize_repo_url("https://github.com/legit-org/legit-repo") == expected
    assert normalize_repo_url("https://github.com/legit-org/legit-repo/") == expected
    assert normalize_repo_url("https://github.com/legit-org/legit-repo.git") == expected
    assert normalize_repo_url("https://github.com/legit-org/legit-repo.git/") == expected
    assert normalize_repo_url("HTTPS://GITHUB.COM/LEGIT-ORG/LEGIT-REPO") == expected
    assert normalize_repo_url("HTTPS://GITHUB.COM/LEGIT-ORG/LEGIT-REPO.GIT/") == expected
    assert normalize_repo_url("") == ""
    assert normalize_repo_url(None) == ""


def test_is_worker_authorized(db_session):
    """Verify worker authorization check for direct matches and DB-linked agents."""
    assert is_worker_authorized("alice", "alice") is True
    assert is_worker_authorized("Alice", "alice") is True
    assert is_worker_authorized("alice", "bob") is False
    assert is_worker_authorized(None, "alice") is False
    assert is_worker_authorized("alice", None) is False

    # Linked agent via address
    agent = Agent(address="ADDR_ALICE", github_username="alice", karma=20)
    db_session.add(agent)
    db_session.commit()

    assert is_worker_authorized("ADDR_ALICE", "alice", db_session) is True
    assert is_worker_authorized("ADDR_ALICE", "bob", db_session) is False


@pytest.mark.asyncio
async def test_mismatched_repo_url_rejected_on_open(db_session):
    """PR event from an unrelated repository must NOT claim or link the bounty."""
    bounty = Bounty(
        bounty_id="b_169",
        status="open",
        creator="creator1",
        amount=5000000,
        repo_url="https://github.com/legit-org/legit-repo"
    )
    db_session.add(bounty)
    db_session.commit()

    payload = {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Malicious PR claiming ALGO-169",
            "body": "Resolves #ALGO-169",
            "state": "open",
            "user": {"login": "attacker"}
        },
        "repository": {
            "html_url": "https://github.com/attacker-org/malicious-repo"
        }
    }

    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)
        mock_post.assert_not_called()

    # Bounty must remain open with no worker assigned
    db_session.refresh(bounty)
    assert bounty.status == "open"
    assert bounty.worker is None

    # No GitHubPR linking record must exist
    linked_pr = db_session.query(GitHubPR).filter(GitHubPR.bounty_id == "b_169").first()
    assert linked_pr is None


@pytest.mark.asyncio
async def test_mismatched_repo_url_rejected_on_merge(db_session):
    """Merged PR from an unrelated repository must NOT close or payout the bounty."""
    bounty = Bounty(
        bounty_id="b_170",
        status="claimed",
        creator="creator1",
        worker="attacker",
        amount=5000000,
        repo_url="https://github.com/legit-org/legit-repo",
        is_hitm=False
    )
    db_session.add(bounty)
    db_session.commit()

    payload = {
        "action": "closed",
        "pull_request": {
            "number": 43,
            "title": "Merged PR on foreign repo ALGO-170",
            "body": "Fixes ALGO-170",
            "state": "closed",
            "merged": True,
            "user": {"login": "attacker"}
        },
        "repository": {
            "html_url": "https://github.com/attacker-org/malicious-repo"
        }
    }

    with patch("gateway.github.release_trustless") as mock_release, \
         patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)
        mock_release.assert_not_called()
        mock_post.assert_not_called()

    db_session.refresh(bounty)
    assert bounty.status == "claimed"


@pytest.mark.asyncio
async def test_matching_repo_url_normalized_success(db_session):
    """PR event with normalized repository matching successfully claims the bounty."""
    bounty = Bounty(
        bounty_id="b_171",
        status="open",
        creator="creator1",
        amount=5000000,
        repo_url="https://github.com/legit-org/legit-repo"
    )
    db_session.add(bounty)
    db_session.commit()

    payload = {
        "action": "opened",
        "pull_request": {
            "number": 1,
            "title": "Fix ALGO-171",
            "body": "Fixes #ALGO-171",
            "state": "open",
            "user": {"login": "legit_worker"}
        },
        "repository": {
            "html_url": "https://github.com/LEGIT-ORG/legit-repo.git/"
        }
    }

    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post, \
         patch("gateway.github._set_commit_status", new_callable=AsyncMock):
        await handle_pr_event(db_session, payload)
        mock_post.assert_called_once()

    db_session.refresh(bounty)
    assert bounty.status == "claimed"
    assert bounty.worker == "legit_worker"

    linked_pr = db_session.query(GitHubPR).filter(GitHubPR.bounty_id == "b_171").first()
    assert linked_pr is not None
    assert linked_pr.pr_number == 1
    assert linked_pr.author == "legit_worker"


@pytest.mark.asyncio
async def test_claim_isolation_rejects_different_author_open(db_session):
    """When a bounty is claimed, another author opening a PR must NOT hijack or transition it."""
    bounty = Bounty(
        bounty_id="b_172",
        status="claimed",
        creator="creator1",
        worker="alice",
        amount=5000000,
        repo_url="https://github.com/legit-org/legit-repo"
    )
    db_session.add(bounty)
    db_session.commit()

    payload = {
        "action": "opened",
        "pull_request": {
            "number": 88,
            "title": "Hijacking ALGO-172",
            "body": "Fixes ALGO-172",
            "state": "open",
            "user": {"login": "bob"}
        },
        "repository": {
            "html_url": "https://github.com/legit-org/legit-repo"
        }
    }

    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)
        mock_post.assert_not_called()

    db_session.refresh(bounty)
    assert bounty.status == "claimed"
    assert bounty.worker == "alice"

    # Bob's PR must NOT be linked to this bounty
    bobs_pr = db_session.query(GitHubPR).filter(
        GitHubPR.bounty_id == "b_172",
        GitHubPR.pr_number == 88
    ).first()
    assert bobs_pr is None


@pytest.mark.asyncio
async def test_claim_isolation_rejects_different_author_sync(db_session):
    """When a bounty is claimed, synchronize from another author must NOT transition to submitted."""
    bounty = Bounty(
        bounty_id="b_173",
        status="claimed",
        creator="creator1",
        worker="alice",
        amount=5000000,
        repo_url="https://github.com/legit-org/legit-repo"
    )
    db_session.add(bounty)
    db_session.commit()

    payload = {
        "action": "synchronize",
        "pull_request": {
            "number": 89,
            "title": "Syncing ALGO-173",
            "body": "Fixes ALGO-173",
            "state": "open",
            "user": {"login": "bob"}
        },
        "repository": {
            "html_url": "https://github.com/legit-org/legit-repo"
        }
    }

    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)
        mock_post.assert_not_called()

    db_session.refresh(bounty)
    assert bounty.status == "claimed"
    assert bounty.worker == "alice"


@pytest.mark.asyncio
async def test_claim_isolation_allows_claimed_worker_sync(db_session):
    """Claimed worker synchronizing their PR successfully transitions bounty to submitted."""
    bounty = Bounty(
        bounty_id="b_174",
        status="claimed",
        creator="creator1",
        worker="alice",
        amount=5000000,
        repo_url="https://github.com/legit-org/legit-repo",
        is_hitm=False
    )
    db_session.add(bounty)
    db_session.commit()

    payload = {
        "action": "synchronize",
        "pull_request": {
            "number": 90,
            "title": "Submit work for ALGO-174",
            "body": "Fixes ALGO-174",
            "state": "open",
            "user": {"login": "alice"}
        },
        "repository": {
            "html_url": "https://github.com/legit-org/legit-repo"
        }
    }

    with patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)
        mock_post.assert_called_once()

    db_session.refresh(bounty)
    assert bounty.status == "submitted"


@pytest.mark.asyncio
async def test_claim_isolation_rejects_unauthorized_merge(db_session):
    """Merged PR from an unauthorized user must NOT trigger payout for another worker's bounty."""
    bounty = Bounty(
        bounty_id="b_175",
        status="submitted",
        creator="creator1",
        worker="alice",
        amount=5000000,
        repo_url="https://github.com/legit-org/legit-repo",
        is_hitm=False
    )
    db_session.add(bounty)
    db_session.commit()

    payload = {
        "action": "closed",
        "pull_request": {
            "number": 91,
            "title": "Bob's PR merged for ALGO-175",
            "body": "Fixes ALGO-175",
            "state": "closed",
            "merged": True,
            "user": {"login": "bob"}
        },
        "repository": {
            "html_url": "https://github.com/legit-org/legit-repo"
        }
    }

    with patch("gateway.github.release_trustless") as mock_release, \
         patch("gateway.github.post_github_comment_and_labels", new_callable=AsyncMock) as mock_post:
        await handle_pr_event(db_session, payload)
        mock_release.assert_not_called()
        mock_post.assert_not_called()

    db_session.refresh(bounty)
    assert bounty.status == "submitted"
