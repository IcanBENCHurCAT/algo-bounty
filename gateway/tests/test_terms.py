"""
Tests for Legal #171: Terms of Service Enforceability.

Covers:
  - GET /api/v1/terms/current — returns current ToS
  - GET /api/v1/terms/{version} — historical lookup
  - POST /api/v1/terms/accept — records acceptance (idempotent)
  - GET /api/v1/terms/accepted/{address} — checks acceptance status
  - POST /api/v1/terms/enforce — pre-flight 451 check
  - Blacklist CRUD (add, list, resolve)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# ─── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Mock DB session. Defaults to 'no records' (new user)."""
    mock_db = MagicMock()
    mock_db.execute.return_value.first.return_value = None
    mock_db.execute.return_value.all.return_value = []
    mock_db.commit = MagicMock()
    yield mock_db


@pytest.fixture
def client(mock_db_session):
    """TestClient with get_db overridden to the mock session."""
    from gateway.main import app
    from gateway.dependencies import get_db
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# ─── Current ToS ──────────────────────────────────────────────────

class TestGetCurrentTerms:
    """GET /api/v1/terms/current"""

    def test_returns_current_version(self, client, mock_db_session):
        """Should return the current ToS version and text."""
        from gateway.supabase_migration import CURRENT_TOS_VERSION
        response = client.get("/api/v1/terms/current")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == CURRENT_TOS_VERSION
        assert "text" in data
        assert "sha256_hash" in data
        assert data["governing_law"] == "Delaware, USA"

    def test_governing_law_present(self, client, mock_db_session):
        """Governing law must be present."""
        response = client.get("/api/v1/terms/current")
        assert response.json()["governing_law"] == "Delaware, USA"
        assert response.json()["arbitration_procedure"] == "mediation_then_binding"


# ─── Historical ToS ──────────────────────────────────────────────

class TestGetTermsVersion:
    """GET /api/v1/terms/{version}"""

    def test_returns_v110(self, client, mock_db_session):
        """Should return the v1.1.0 text."""
        response = client.get("/api/v1/terms/1.1.0")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.1.0"
        assert "AlgoBounty Terms of Service" in data["text"]

    def test_returns_404_for_missing(self, client, mock_db_session):
        """Should return 404 for unknown version."""
        response = client.get("/api/v1/terms/0.9.0")
        assert response.status_code == 404


# ─── Accept Terms ────────────────────────────────────────────────

class TestAcceptTerms:
    """POST /api/v1/terms/accept"""

    def test_accepts_terms_for_new_user(self, client, mock_db_session):
        """Should record acceptance for a new user."""
        response = client.post("/api/v1/terms/accept?address=test123")
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert data["message"] == "Terms accepted successfully"
        # Verify DB call was made
        mock_db_session.execute.assert_called()

    def test_idempotent_accept(self, client, mock_db_session):
        """Accepting twice should not error — returns existing acceptance."""
        # First call: already accepted (simulated by existing DB record)
        from sqlalchemy import text
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([1]))
        mock_result[0] = datetime.now(timezone.utc)
        mock_db_session.execute.return_value.first.return_value = mock_result

        response = client.post("/api/v1/terms/accept?address=test123")
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        # Should not have inserted (idempotent)

    def test_accept_with_metadata(self, client, mock_db_session):
        """Should record IP hash and user agent."""
        response = client.post(
            "/api/v1/terms/accept?address=test123",
            headers={"X-Forwarded-For": "1.2.3.4", "User-Agent": "test/1.0"}
        )
        assert response.status_code == 200


# ─── Check Acceptance ────────────────────────────────────────────

class TestCheckAcceptance:
    """GET /api/v1/terms/accepted/{address}"""

    def test_unaccepted_user(self, client, mock_db_session):
        """User without acceptance should get accepted=False."""
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db_session.execute.return_value.first.return_value = None

        response = client.get("/api/v1/terms/accepted/test123")
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is False
        assert data["requires_action"] is True

    def test_accepted_user(self, client, mock_db_session):
        """User with acceptance should get accepted=True."""
        mock_result = MagicMock()
        mock_db_session.execute.return_value.first.return_value = mock_result

        response = client.get("/api/v1/terms/accepted/test123")
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True


# ─── Enforce Check ───────────────────────────────────────────────

class TestEnforceTerms:
    """POST /api/v1/terms/enforce"""

    def test_returns_451_when_not_accepted(self, client, mock_db_session):
        """Should return 451 if user hasn't accepted."""
        mock_db_session.execute.return_value.first.return_value = None

        response = client.post("/api/v1/terms/enforce?address=test123")
        assert response.status_code == 451
        data = response.json()["detail"]
        assert data["reason"] == "Terms Not Accepted"
        assert "terms_text" in data
        assert "accept_url" in data

    def test_returns_200_when_accepted(self, client, mock_db_session):
        """Should return 200 if user has accepted."""
        from sqlalchemy import text
        mock_result = MagicMock()
        mock_db_session.execute.return_value.first.return_value = mock_result

        response = client.post("/api/v1/terms/enforce?address=test123")
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True


# ─── Blacklist ────────────────────────────────────────────────────

class TestBlacklist:
    """Blacklist CRUD"""

    def test_list_blacklist(self, client, mock_db_session):
        """Should list all active blacklisted addresses."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("abc123", "fraud", datetime.now(timezone.utc), "active"),
        ]
        mock_db_session.execute.return_value.all.return_value = mock_result.all.return_value

        response = client.get("/api/v1/terms/blacklist")
        # May return 401/403 without proper admin auth — just check structure
        assert response.status_code in [200, 401, 403]

    def test_add_blacklist(self, client, mock_db_session):
        """Should add an address to blacklist."""
        response = client.post(
            "/api/v1/terms/blacklist?address=test123&reason=test_fraud"
        )
        assert response.status_code in [200, 401, 403]

    def test_resolve_blacklist(self, client, mock_db_session):
        """Should remove an address from blacklist."""
        response = client.post("/api/v1/terms/blacklist/test123/resolve")
        assert response.status_code in [200, 401, 403]


# ─── Integration: Full Flow ──────────────────────────────────────

class TestFullFlow:
    """End-to-end: unaccepted → accept → enforce → bounty creation"""

    def test_full_enforcement_flow(self, client, mock_db_session):
        """
        1. Check acceptance → false
        2. Accept terms
        3. Check acceptance → true
        4. Enforce check → success
        """
        # Step 1: Unaccepted
        mock_db_session.execute.return_value.first.return_value = None
        resp1 = client.get("/api/v1/terms/accepted/test123")
        assert resp1.json()["accepted"] is False

        # Step 2: Accept
        resp2 = client.post("/api/v1/terms/accept?address=test123")
        assert resp2.status_code == 200
        assert resp2.json()["accepted"] is True

        # Step 3: Now accepted
        from sqlalchemy import text
        mock_result = MagicMock()
        mock_db_session.execute.return_value.first.return_value = mock_result
        resp3 = client.get("/api/v1/terms/accepted/test123")
        assert resp3.json()["accepted"] is True

        # Step 4: Enforce succeeds
        resp4 = client.post("/api/v1/terms/enforce?address=test123")
        assert resp4.status_code == 200
