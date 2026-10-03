"""Tests for Legal #165 — Agent Stewardship enforcement."""

import os, sys, pytest
from unittest.mock import patch
from gateway.database import Agent, Bounty

# Conftest get_auth_token helper (defined in tests/conftest.py)
sys.path.insert(0, os.path.dirname(__file__))
from conftest import get_auth_token


# ─── Test Steward Registration ───────────────────────────────────────


class TestStewardRegistration:
    def test_register_steward(self, client, db_session):
        """Register a steward for an agent."""
        addr = "STEW_TEST_AGENT_0000000000000000000000000001"
        agent = Agent(address=addr, karma=100)
        db_session.add(agent)
        db_session.commit()

        token = get_auth_token(client, addr)
        headers = {"Authorization": f"Bearer {token}"}

        res = client.put(
            "/api/v1/agents/me/steward",
            json={
                "steward_name": "Jane Steward",
                "steward_email": "jane@example.com",
                "steward_stablecoin_address": "USDCaddr0000000000000000000001",
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "registered"
        assert data["steward_name"] == "Jane Steward"
        assert data["steward_email"] == "jane@example.com"
        assert data["steward_verified"] is True

        # Verify in DB
        db_agent = db_session.query(Agent).filter(Agent.address == addr).first()
        assert db_agent.steward_name == "Jane Steward"
        assert db_agent.steward_verified is True

    def test_register_steward_missing_auth(self, client, db_session):
        """Register steward without authentication."""
        res = client.put(
            "/api/v1/agents/me/steward",
            json={"steward_name": "Bob", "steward_email": "bob@test.com"},
        )
        assert res.status_code == 401

    def test_register_steward_no_profile(self, client, db_session):
        """Register steward for non-existent agent — returns 404."""
        token = get_auth_token(client, "NONEXISTENT_AGENT_000000000000001")
        # auth auto-creates the agent profile; delete it to exercise the 404 path
        db_session.query(Agent).filter(Agent.address == "NONEXISTENT_AGENT_000000000000001").delete()
        db_session.commit()
        res = client.put(
            "/api/v1/agents/me/steward",
            json={"steward_name": "Bob", "steward_email": "bob@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should return 404 since agent doesn't exist
        assert res.status_code == 404


# ─── Stewardship Enforcement — Bounty Creation ───────────────────────


class TestBountyCreationStewardship:
    def test_create_bounty_without_steward(self, client, db_session):
        """Cannot create bounty without registered steward."""
        addr = "STEW_NO_STEWARD_000000000000000000000001"
        agent = Agent(address=addr, karma=100)
        db_session.add(agent)
        db_session.commit()

        token = get_auth_token(client, addr)
        res = client.post(
            "/api/v1/bounties",
            json={
                "description": "Test bounty",
                "amount": 1000000,
                "repo_url": "https://github.com/test/repo",
                "app_id": 999,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert "steward" in res.json()["detail"].lower()

    def test_create_bounty_unverified_steward(self, client, db_session):
        """Cannot create bounty with unverified steward."""
        addr = "STEW_UNVERIFIED_00000000000000000000001"
        agent = Agent(
            address=addr,
            karma=100,
            steward_name="Jane Steward",
            steward_email="jane@example.com",
            steward_verified=False,
        )
        db_session.add(agent)
        db_session.commit()

        token = get_auth_token(client, addr)
        res = client.post(
            "/api/v1/bounties",
            json={
                "description": "Test bounty",
                "amount": 1000000,
                "repo_url": "https://github.com/test/repo",
                "app_id": 999,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert "not verified" in res.json()["detail"].lower()

    def test_create_bounty_with_verified_steward(self, client, db_session):
        """Can create bounty with verified steward."""
        addr = "STEW_VERIFIED_000000000000000000000001"
        agent = Agent(
            address=addr,
            karma=100,
            steward_name="Jane Steward",
            steward_email="jane@example.com",
            steward_verified=True,
        )
        db_session.add(agent)
        db_session.commit()

        token = get_auth_token(client, addr)
        res = client.post(
            "/api/v1/bounties",
            json={
                "description": "Test bounty",
                "amount": 1000000,
                "repo_url": "https://github.com/test/repo",
                "app_id": 999,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200


# ─── Stewardship Enforcement — Bounty Claim ──────────────────────────


class TestBountyClaimStewardship:
    def test_claim_bounty_without_steward(self, client, db_session, seeded_agents):
        """Cannot claim bounty without registered steward."""
        creator_addr = seeded_agents[0].address
        worker_addr = seeded_agents[1].address

        # seeded_agents ships with verified stewards; strip them for this negative test
        worker = db_session.query(Agent).filter(Agent.address == worker_addr).first()
        worker.steward_name = None
        worker.steward_email = None
        worker.steward_verified = False
        db_session.commit()

        bounty = Bounty(
            bounty_id="b_steward_claim_test",
            app_id=42,
            status="open",
            creator=creator_addr,
            amount=10000000,
            repo_url="https://github.com/test/repo",
        )
        db_session.add(bounty)
        db_session.commit()

        token = get_auth_token(client, worker_addr)
        res = client.post(
            f"/api/v1/bounties/b_steward_claim_test/claim",
            json={"signed_txn": "fake"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert "steward" in res.json()["detail"].lower()

    def test_claim_bounty_unverified_steward(self, client, db_session, seeded_agents):
        """Cannot claim bounty with unverified steward."""
        creator_addr = seeded_agents[0].address
        worker_addr = seeded_agents[1].address

        worker = db_session.query(Agent).filter(Agent.address == worker_addr).first()
        worker.steward_name = "Jane Steward"
        worker.steward_email = "jane@example.com"
        worker.steward_verified = False
        db_session.commit()

        bounty = Bounty(
            bounty_id="b_steward_claim_unver",
            app_id=43,
            status="open",
            creator=creator_addr,
            amount=10000000,
            repo_url="https://github.com/test/repo",
        )
        db_session.add(bounty)
        db_session.commit()

        token = get_auth_token(client, worker_addr)
        res = client.post(
            f"/api/v1/bounties/b_steward_claim_unver/claim",
            json={"signed_txn": "fake"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert "not verified" in res.json()["detail"].lower()

    def test_claim_bounty_with_verified_steward(self, client, db_session, seeded_agents):
        """Can claim bounty with verified steward — mock send_signed_transaction."""
        creator_addr = seeded_agents[0].address
        worker_addr = seeded_agents[1].address

        worker = db_session.query(Agent).filter(Agent.address == worker_addr).first()
        worker.steward_name = "Jane Steward"
        worker.steward_email = "jane@example.com"
        worker.steward_verified = True
        db_session.commit()

        bounty = Bounty(
            bounty_id="b_steward_claim_ver",
            app_id=44,
            status="open",
            creator=creator_addr,
            amount=10000000,
            repo_url="https://github.com/test/repo",
        )
        db_session.add(bounty)
        db_session.commit()

        token = get_auth_token(client, worker_addr)
        with patch("gateway.routers.bounties.send_signed_transaction", return_value="fake_txid"):
            res = client.post(
                f"/api/v1/bounties/b_steward_claim_ver/claim",
                json={"signed_txn": "fake"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert res.status_code == 200
        assert res.json()["status"] == "claimed"


# ─── Steward Lookup ──────────────────────────────────────────────────


class TestStewardLookup:
    def test_list_agents_for_steward(self, client, db_session):
        """List all agents for a steward address."""
        steward_addr = "STEW_WALLET_000000000000000000000000001"

        for suffix in ["001", "002"]:
            agent = Agent(
                address=f"AGENT_{suffix}",
                karma=50,
                steward_name="Team Steward",
                steward_email="team@example.com",
                steward_verified=True,
                steward_of_steward_address=steward_addr,
            )
            db_session.add(agent)
        db_session.commit()

        res = client.get(f"/api/v1/agents/steward/{steward_addr}")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        for item in data:
            assert item["steward_of_steward_address"] == steward_addr
            assert item["steward_name"] == "Team Steward"

    def test_list_agents_for_unknown_steward(self, client):
        """Return empty list for unknown steward."""
        res = client.get("/api/v1/agents/steward/UNKNOWN_STEW_00000000000001")
        assert res.status_code == 200
        assert res.json() == []


# ─── Agent Profile Response ──────────────────────────────────────────


class TestAgentProfileResponse:
    def test_profile_includes_steward_fields(self, client, db_session):
        """Agent profile includes all steward fields."""
        addr = "STEW_PROFILE_00000000000000000000000001"
        agent = Agent(
            address=addr,
            karma=100,
            steward_name="Jane Steward",
            steward_email="jane@example.com",
            steward_verified=True,
            steward_stablecoin_address="USDCaddr0000000000000000000001",
        )
        db_session.add(agent)
        db_session.commit()

        token = get_auth_token(client, addr)
        res = client.get(
            "/api/v1/agents/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "steward_name" in data
        assert "steward_email" in data
        assert "steward_verified" in data
        assert data["steward_name"] == "Jane Steward"
        assert data["steward_verified"] is True

    def test_profile_without_steward(self, client, db_session):
        """Agent profile returns null/default for steward fields when not registered."""
        addr = "STEW_NO_REG_00000000000000000000000001"
        agent = Agent(address=addr, karma=100)
        db_session.add(agent)
        db_session.commit()

        token = get_auth_token(client, addr)
        res = client.get(
            "/api/v1/agents/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["steward_name"] is None
        assert data["steward_verified"] is False
