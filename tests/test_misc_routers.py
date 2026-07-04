import pytest
from unittest.mock import patch
from gateway.database import Agent, Notification

def test_get_agent_me(client, seeded_agents):
    from tests.conftest import get_auth_token
    token = get_auth_token(client, "CREATOR_ADDR")
    res = client.get("/api/v1/agents/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["address"] == "CREATOR_ADDR"
    assert res.json()["karma"] == 50

def test_get_agent_profile(client, seeded_agents):
    res = client.get("/api/v1/agents/WORKER_ADDR")
    assert res.status_code == 200
    assert res.json()["address"] == "WORKER_ADDR"

def test_list_notifications(client, seeded_agents, db_session):
    db_session.add(Notification(recipient="CREATOR_ADDR", message="Hello"))
    db_session.commit()

    from tests.conftest import get_auth_token
    token = get_auth_token(client, "CREATOR_ADDR")
    res = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["message"] == "Hello"

def test_mark_notification_read(client, seeded_agents, db_session):
    # Get token first to ensure agent exists
    from tests.conftest import get_auth_token
    token = get_auth_token(client, "CREATOR_ADDR")

    notif = Notification(recipient="CREATOR_ADDR", message="Hello")
    db_session.add(notif)
    db_session.commit()

    res = client.post(f"/api/v1/notifications/{notif.id}/read", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    db_session.refresh(notif)
    assert notif.read is True

def test_events_stream_endpoint(client):
    res = client.get("/api/v1/events")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")

def test_oidc_verify_endpoint_exceptions(client):
    import jwt
    # 1. Expired signature
    with patch("gateway.routers.oidc.verify_github_oidc_token", side_effect=jwt.ExpiredSignatureError("expired")):
        res = client.post("/api/v1/oidc/verify", json={"token": "t"})
        assert res.status_code == 401
        assert "Token expired" in res.json()["detail"]

    # 2. Invalid token
    with patch("gateway.routers.oidc.verify_github_oidc_token", side_effect=jwt.InvalidTokenError("invalid")):
        res = client.post("/api/v1/oidc/verify", json={"token": "t"})
        assert res.status_code == 400
        assert "Invalid token" in res.json()["detail"]

    # 3. Verification error
    with patch("gateway.routers.oidc.verify_github_oidc_token", side_effect=Exception("verification failed")):
        res = client.post("/api/v1/oidc/verify", json={"token": "t"})
        assert res.status_code == 500
        assert "Verification error" in res.json()["detail"]

