import pytest
from unittest.mock import patch, MagicMock
from gateway.database import Bounty

def test_list_bounties_filters(client, db_session):
    # Seed data
    db_session.add(Bounty(bounty_id="b1", status="open", creator="C1", amount=1000, repo_url="repo1", karma_requirement=0, is_hitm=False))
    db_session.add(Bounty(bounty_id="b2", status="claimed", creator="C1", amount=2000, repo_url="repo2", karma_requirement=10, is_hitm=True))
    db_session.add(Bounty(bounty_id="b3", status="open", creator="C2", amount=500, repo_url="repo1/sub", karma_requirement=5, is_hitm=False))
    db_session.commit()

    # Filter by status
    res = client.get("/api/v1/bounties?status=claimed")
    assert res.status_code == 200
    assert len(res.json()["bounties"]) == 1
    assert res.json()["bounties"][0]["bounty_id"] == "b2"

    # Filter by repo (contains)
    res = client.get("/api/v1/bounties?repo=repo1")
    assert res.status_code == 200
    assert len(res.json()["bounties"]) == 2

    # Filter by amount
    res = client.get("/api/v1/bounties?min_amount=1500")
    assert res.status_code == 200
    assert len(res.json()["bounties"]) == 1
    assert res.json()["bounties"][0]["bounty_id"] == "b2"

    # Filter by karma
    res = client.get("/api/v1/bounties?min_karma=10")
    assert res.status_code == 200
    assert len(res.json()["bounties"]) == 1
    assert res.json()["bounties"][0]["bounty_id"] == "b2"

    # Filter by hitm
    res = client.get("/api/v1/bounties?hitm=true")
    assert res.status_code == 200
    assert len(res.json()["bounties"]) == 1
    assert res.json()["bounties"][0]["bounty_id"] == "b2"

def test_get_bounty_not_found(client):
    res = client.get("/api/v1/bounties/nonexistent")
    assert res.status_code == 404

def test_get_bounty_onchain(client, db_session):
    # Bounty with app_id
    b = Bounty(bounty_id="b1", status="open", creator="C1", amount=1000, repo_url="repo1", app_id=12345)
    db_session.add(b)
    db_session.commit()

    mock_algod = MagicMock()
    mock_algod.application_info.return_value = {"last-round": 100}

    with patch("gateway.routers.bounties.get_algod_client", return_value=mock_algod):
        res = client.get("/api/v1/bounties/b1/onchain")
        assert res.status_code == 200
        assert res.json()["onchain"] is True
        assert res.json()["app_id"] == 12345

def test_get_bounty_onchain_error(client, db_session):
    b = Bounty(bounty_id="b1", status="open", creator="C1", amount=1000, repo_url="repo1", app_id=12345)
    db_session.add(b)
    db_session.commit()

    mock_algod = MagicMock()
    mock_algod.application_info.side_effect = Exception("Node error")

    with patch("gateway.routers.bounties.get_algod_client", return_value=mock_algod):
        res = client.get("/api/v1/bounties/b1/onchain")
        assert res.status_code == 200
        assert res.json()["onchain"] is False
        assert "Node error" in res.json()["error"]
