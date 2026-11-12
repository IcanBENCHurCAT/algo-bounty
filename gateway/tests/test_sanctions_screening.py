"""
Tests for Issue #180: Sanctions Screening: OFAC/PEP at Point of Entry via KYA.

Covers:
1. Config flag REQUIRE_SCREENING: bool = False in gateway/config.py
2. KYA screening integration (POST /api/v1/screen) via respx
3. Local evaluator fallback (OFAC lists, PEP, DB blacklist)
4. Audit hash generation and screened_at timestamp persistence
5. Bounty creation flow:
   - Creator address screened at point of entry
   - Screening status ('pending', 'passed', 'flagged', 'blocked') saved
   - REQUIRE_SCREENING=False: blocked address allowed and saved as 'blocked'
   - REQUIRE_SCREENING=True: blocked address rejected with 403 Forbidden
   - REQUIRE_SCREENING=True: flagged address accepted and saved as 'flagged'
   - Passed address accepted and saved as 'passed'
6. Verification via respx and unittest.mock
"""

import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
import respx
import httpx
from fastapi.testclient import TestClient

from gateway.config import settings, REQUIRE_SCREENING
from gateway.screening import (
    screen_address,
    screen_address_async,
    evaluate_locally,
    compute_screening_hash,
    SCREENING_STATUS_PASSED,
    SCREENING_STATUS_FLAGGED,
    SCREENING_STATUS_BLOCKED,
    SCREENING_STATUS_PENDING,
    ScreeningResult,
)
from gateway.database import Bounty, Agent, UserBlacklist
from gateway.main import app
from gateway.dependencies import get_db
from gateway.auth import get_current_user


# ─── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def creator_agent(db_session):
    """Seed a fully verified agent capable of creating bounties."""
    addr = "TEST_CREATOR_ALGORAND_ADDRESS_CLEAN_001"
    agent = db_session.query(Agent).filter(Agent.address == addr).first()
    if not agent:
        agent = Agent(
            address=addr,
            karma=100,
            steward_name="Steward Jane",
            steward_email="jane@example.com",
            steward_verified=True,
        )
        db_session.add(agent)
        db_session.commit()
    return agent


@pytest.fixture
def client(db_session, creator_agent):
    """TestClient with get_db and get_current_user overridden."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: creator_agent.address
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ─── 1. Configuration Flag Tests ──────────────────────────────────────

class TestConfigFlag:
    """Requirement 4: Add config flag REQUIRE_SCREENING: bool = False in gateway/config.py"""

    def test_default_require_screening_is_false(self):
        """Default REQUIRE_SCREENING must be False."""
        assert settings.REQUIRE_SCREENING is False
        assert REQUIRE_SCREENING is False

    def test_setter_and_deleter_updates_flag(self):
        """Direct attribute assignment on settings toggles the flag."""
        settings.REQUIRE_SCREENING = True
        assert settings.REQUIRE_SCREENING is True
        settings.REQUIRE_SCREENING = False
        assert settings.REQUIRE_SCREENING is False
        del settings.REQUIRE_SCREENING

    def test_env_var_enables_screening(self):
        """Environment variable REQUIRE_SCREENING=true activates screening."""
        with patch.dict(os.environ, {"REQUIRE_SCREENING": "true"}):
            assert settings.REQUIRE_SCREENING is True
        with patch.dict(os.environ, {"REQUIRE_SCREENING": "1"}):
            assert settings.REQUIRE_SCREENING is True
        with patch.dict(os.environ, {"REQUIRE_SCREENING": "false"}):
            assert settings.REQUIRE_SCREENING is False

    def test_patch_object_support(self):
        """patch.object(settings, 'REQUIRE_SCREENING', ...) cleanly enters and exits."""
        with patch.object(settings, "REQUIRE_SCREENING", True):
            assert settings.REQUIRE_SCREENING is True
        assert settings.REQUIRE_SCREENING is False


# ─── 2. KYA Screening & respx Integration Tests ───────────────────────

class TestKYAScreeningUnit:
    """Requirements 1, 3, 5: KYA endpoint calling via respx, mock, and audit hash."""

    @respx.mock
    def test_kya_screen_passed(self):
        """KYA service returns 'passed' for clean address."""
        kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
        respx.post(kya_url).respond(
            status_code=200,
            json={
                "status": "passed",
                "sanctions_match": False,
                "pep_match": False,
                "risk_score": 0.0,
                "reason": "No match found",
            },
        )

        result = screen_address("CLEAN_WALLET_ADDRESS_123")
        assert result.status == SCREENING_STATUS_PASSED
        assert result.sanctions_match is False
        assert result.pep_match is False
        assert result.risk_score == 0.0
        assert result.screening_hash is not None
        assert len(result.screening_hash) == 64  # SHA256 length
        assert isinstance(result.screened_at, datetime)

    @respx.mock
    def test_kya_screen_blocked(self):
        """KYA service returns 'blocked' for sanctioned address."""
        kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
        respx.post(kya_url).respond(
            status_code=200,
            json={
                "status": "blocked",
                "sanctions_match": True,
                "reason": "OFAC Specially Designated National",
                "risk_score": 1.0,
            },
        )

        result = screen_address("SANCTIONED_ADDRESS_XYZ")
        assert result.status == SCREENING_STATUS_BLOCKED
        assert result.sanctions_match is True
        assert result.reason == "OFAC Specially Designated National"
        assert result.risk_score == 1.0
        assert result.screening_hash is not None

    @respx.mock
    def test_kya_screen_flagged(self):
        """KYA service returns 'flagged' for PEP watchlist address."""
        kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
        respx.post(kya_url).respond(
            status_code=200,
            json={
                "status": "flagged",
                "pep_match": True,
                "risk_score": 0.85,
                "reason": "PEP Watchlist",
            },
        )

        result = screen_address("PEP_ADDRESS_XYZ")
        assert result.status == SCREENING_STATUS_FLAGGED
        assert result.pep_match is True
        assert result.risk_score == 0.85

    @respx.mock
    def test_kya_screen_http_403_blocked(self):
        """KYA service returning HTTP 403 Forbidden maps to blocked status."""
        kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
        respx.post(kya_url).respond(
            status_code=403,
            json={
                "status": "blocked",
                "reason": "Direct OFAC match",
            },
        )

        result = screen_address("BLOCKED_ENTITY_ADDRESS")
        assert result.status == SCREENING_STATUS_BLOCKED

    @respx.mock
    @pytest.mark.asyncio
    async def test_kya_screen_async_variant(self):
        """Async variant screen_address_async works cleanly."""
        kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
        respx.post(kya_url).respond(
            status_code=200,
            json={"status": "passed", "sanctions_match": False},
        )

        result = await screen_address_async("ASYNC_CLEAN_ADDRESS")
        assert result.status == SCREENING_STATUS_PASSED

    def test_audit_hash_deterministic(self):
        """Audit hash is deterministic and tamper-evident."""
        now = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
        h1 = compute_screening_hash("ADDR1", "passed", now)
        h2 = compute_screening_hash("ADDR1", "passed", now)
        h3 = compute_screening_hash("ADDR1", "blocked", now)
        assert h1 == h2
        assert h1 != h3


# ─── 3. Local Evaluator Fallback Tests ────────────────────────────────

class TestLocalEvaluator:
    """Local sanctions evaluator for offline operation and network fallback."""

    def test_clean_address_passes(self):
        result = evaluate_locally("CLEAN_ALGORAND_WALLET_ABC123")
        assert result.status == SCREENING_STATUS_PASSED
        assert result.sanctions_match is False
        assert result.pep_match is False
        assert result.risk_score == 0.0

    def test_sanctioned_pattern_blocked(self):
        result = evaluate_locally("WALLET_SANCTIONED_BY_OFAC")
        assert result.status == SCREENING_STATUS_BLOCKED
        assert result.sanctions_match is True
        assert result.risk_score == 1.0

    def test_pep_pattern_flagged(self):
        result = evaluate_locally("WALLET_PEP_FLAGGED_123")
        assert result.status == SCREENING_STATUS_FLAGGED
        assert result.pep_match is True
        assert result.risk_score == 0.75

    def test_db_blacklist_blocked(self, db_session):
        blacklisted_addr = "BLACKLISTED_WALLET_IN_DB_999"
        bl = UserBlacklist(
            address=blacklisted_addr,
            reason="Terrorism financing / OFAC match",
            status="active",
        )
        db_session.add(bl)
        db_session.commit()

        result = evaluate_locally(blacklisted_addr, db=db_session)
        assert result.status == SCREENING_STATUS_BLOCKED
        assert "Terrorism financing" in result.reason

    @respx.mock
    def test_kya_connection_failure_falls_back_to_local(self):
        """If external KYA server fails with ConnectError, falls back to local evaluator."""
        kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
        respx.post(kya_url).mock(side_effect=httpx.ConnectError("Connection refused"))

        # Clean address -> local evaluator passes
        result = screen_address("CLEAN_ADDRESS_NO_KYA_SERVER")
        assert result.status == SCREENING_STATUS_PASSED

        # Known blocked address -> local evaluator blocks
        blocked_result = screen_address("OFAC_BLOCKED_ADDRESS")
        assert blocked_result.status == SCREENING_STATUS_BLOCKED


# ─── 4. Bounty Creation Flow Tests ────────────────────────────────────

class TestBountyCreationSanctionsFlow:
    """
    Requirements 1, 2, 5, 6:
    - Creator's address screened at bounty creation
    - screening_status, screened_at, screening_hash saved
    - REQUIRE_SCREENING=False: blocked address allowed and saved as 'blocked'
    - REQUIRE_SCREENING=True: blocked address rejected with 403 Forbidden
    - REQUIRE_SCREENING=True: flagged address accepted and saved as 'flagged'
    """

    payload = {
        "description": "Smart Contract Audit Bounty",
        "amount": 1000000,
        "asset_id": 0,
        "repo_url": "https://github.com/IcanBENCHurCAT/algo-bounty",
        "karma_requirement": 0,
    }

    def test_creation_clean_address_passes(self, client, db_session, creator_agent):
        """Clean creator address results in passed screening_status and audit hash."""
        with patch("gateway.screening.screen_address") as mock_screen:
            mock_screen.return_value = ScreeningResult(
                status=SCREENING_STATUS_PASSED,
                address=creator_agent.address,
                screened_at=datetime.now(timezone.utc),
                screening_hash="mock_passed_hash_1234567890abcdef",
            )
            resp = client.post("/api/v1/bounties", json=self.payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["screening_status"] == SCREENING_STATUS_PASSED
        assert data["screening_hash"] == "mock_passed_hash_1234567890abcdef"
        assert data["screened_at"] is not None

        # Verify DB record
        bounty = db_session.query(Bounty).filter(Bounty.bounty_id == data["bounty_id"]).first()
        assert bounty is not None
        assert bounty.screening_status == SCREENING_STATUS_PASSED
        assert bounty.screening_hash == "mock_passed_hash_1234567890abcdef"
        assert bounty.screened_at is not None

    def test_creation_require_screening_disabled_allows_blocked(self, client, db_session, creator_agent):
        """When REQUIRE_SCREENING=False, blocked creator is allowed; saved as 'blocked'."""
        with patch.object(settings, "REQUIRE_SCREENING", False):
            with patch("gateway.screening.screen_address") as mock_screen:
                mock_screen.return_value = ScreeningResult(
                    status=SCREENING_STATUS_BLOCKED,
                    address=creator_agent.address,
                    screened_at=datetime.now(timezone.utc),
                    screening_hash="mock_blocked_hash_abcdef1234567890",
                    sanctions_match=True,
                    reason="OFAC SDN match",
                )
                resp = client.post("/api/v1/bounties", json=self.payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["screening_status"] == SCREENING_STATUS_BLOCKED
        assert data["screening_hash"] == "mock_blocked_hash_abcdef1234567890"

        # Stored in DB as blocked
        b = db_session.query(Bounty).filter(Bounty.bounty_id == data["bounty_id"]).first()
        assert b.screening_status == SCREENING_STATUS_BLOCKED
        assert b.screening_hash == "mock_blocked_hash_abcdef1234567890"

    def test_creation_require_screening_enabled_rejects_blocked_403(self, client, db_session, creator_agent):
        """When REQUIRE_SCREENING=True and screening returns 'blocked', reject with 403 Forbidden."""
        with patch.object(settings, "REQUIRE_SCREENING", True):
            with patch("gateway.screening.screen_address") as mock_screen:
                mock_screen.return_value = ScreeningResult(
                    status=SCREENING_STATUS_BLOCKED,
                    address=creator_agent.address,
                    screened_at=datetime.now(timezone.utc),
                    screening_hash="mock_blocked_audit_hash",
                    sanctions_match=True,
                    reason="OFAC SDN match",
                )
                resp = client.post("/api/v1/bounties", json=self.payload)

        assert resp.status_code == 403
        assert "Sanctions screening blocked" in resp.json()["detail"]

        # Ensure no bounty was committed to DB
        b = db_session.query(Bounty).filter(Bounty.creator == creator_agent.address).first()
        assert b is None

    def test_creation_require_screening_enabled_saves_flagged(self, client, db_session, creator_agent):
        """When REQUIRE_SCREENING=True and screening returns 'flagged', save as flagged."""
        with patch.object(settings, "REQUIRE_SCREENING", True):
            with patch("gateway.screening.screen_address") as mock_screen:
                mock_screen.return_value = ScreeningResult(
                    status=SCREENING_STATUS_FLAGGED,
                    address=creator_agent.address,
                    screened_at=datetime.now(timezone.utc),
                    screening_hash="mock_flagged_audit_hash",
                    pep_match=True,
                    reason="PEP high risk",
                )
                resp = client.post("/api/v1/bounties", json=self.payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["screening_status"] == SCREENING_STATUS_FLAGGED
        assert data["screening_hash"] == "mock_flagged_audit_hash"

        # Stored in DB as flagged
        b = db_session.query(Bounty).filter(Bounty.bounty_id == data["bounty_id"]).first()
        assert b.screening_status == SCREENING_STATUS_FLAGGED

    @respx.mock
    def test_creation_with_respx_kya_blocked(self, client, db_session, creator_agent):
        """End-to-end integration with respx mocking the KYA endpoint."""
        kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
        respx.post(kya_url).respond(
            status_code=200,
            json={
                "status": "blocked",
                "sanctions_match": True,
                "reason": "Direct OFAC SDN match",
            },
        )

        with patch.object(settings, "REQUIRE_SCREENING", True):
            resp = client.post("/api/v1/bounties", json=self.payload)

        assert resp.status_code == 403
        assert "Direct OFAC SDN match" in resp.json()["detail"]

    def test_get_and_list_bounties_includes_screening_status(self, client, db_session, creator_agent):
        """GET /api/v1/bounties and GET /api/v1/bounties/{id} return screening fields."""
        bounty = Bounty(
            bounty_id="b_screen_test_180",
            status="open",
            creator=creator_agent.address,
            amount=5000000,
            repo_url="https://github.com/IcanBENCHurCAT/algo-bounty",
            screening_status="flagged",
            screened_at=datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc),
            screening_hash="hash_screen_180_audit",
        )
        db_session.add(bounty)
        db_session.commit()

        # 1. GET by id
        get_resp = client.get("/api/v1/bounties/b_screen_test_180")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["screening_status"] == "flagged"
        assert get_data["screening_hash"] == "hash_screen_180_audit"
        assert get_data["screened_at"] is not None

        # 2. List with filter
        list_resp = client.get("/api/v1/bounties?screening_status=flagged")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        matched = [b for b in list_data["bounties"] if b["bounty_id"] == "b_screen_test_180"]
        assert len(matched) == 1
        assert matched[0]["screening_status"] == "flagged"


# ─── 5. Direct Screening API Endpoints ────────────────────────────────

class TestScreeningAPIEndpoints:
    """Gateway API endpoints /api/v1/screening/screen and /api/v1/screening/{address}."""

    def test_post_screen_endpoint(self, client):
        resp = client.post("/api/v1/screening/screen", json={"address": "ANY_WALLET_ADDR_CLEAN"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("passed", "flagged", "blocked", "pending")
        assert data["screening_hash"] is not None
        assert data["screened_at"] is not None

    def test_get_screening_endpoint(self, client):
        resp = client.get("/api/v1/screening/OFAC_BLOCKED_ADDRESS")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "blocked"
        assert data["sanctions_match"] is True

    def test_screening_normalization_case_and_whitespace(self, client):
        """Verify lowercase and whitespace-padded inputs cannot bypass sanctions screening."""
        # Lowercase test
        lower_resp = client.post("/api/v1/screening/screen", json={"address": "tornado_cash_router"})
        assert lower_resp.status_code == 200
        assert lower_resp.json()["status"] == "blocked"
        assert lower_resp.json()["sanctions_match"] is True

        # Whitespace-padded test
        padded_resp = client.post("/api/v1/screening/screen", json={"address": "  TORNADO_CASH_ROUTER  "})
        assert padded_resp.status_code == 200
        assert padded_resp.json()["status"] == "blocked"
        assert padded_resp.json()["sanctions_match"] is True

        # PEP flagged lowercase and padded
        pep_resp = client.post("/api/v1/screening/screen", json={"address": "  pep_flagged_test_address  "})
        assert pep_resp.status_code == 200
        assert pep_resp.json()["status"] == "flagged"
        assert pep_resp.json()["pep_match"] is True
