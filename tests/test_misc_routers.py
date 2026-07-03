import pytest
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
