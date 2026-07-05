import pytest
from unittest.mock import patch, MagicMock
from gateway.indexer import poll_bounty_events, fetch_app_logs

def test_poll_bounty_events():
    mock_indexer = MagicMock()
    mock_indexer.search_applications.return_value = {
        "applications": [
            {"id": 100, "params": {"approval-program": "prog1"}},
            {"id": 101, "params": {"approval-program": "prog2"}}
        ],
        "current-round": 500
    }

    with patch("gateway.indexer.get_indexer_client", return_value=mock_indexer):
        events = poll_bounty_events(0)
        assert len(events) == 2
        assert events[0]["app_id"] == 100
        assert events[1]["app_id"] == 101
        assert events[0]["round"] == 500

def test_fetch_app_logs():
    mock_indexer = MagicMock()
    mock_indexer.search_transactions.return_value = {
        "transactions": [
            {
                "id": "TX1",
                "confirmed-round": 450,
                "logs": ["bG9nMQ=="] # "log1" in b64
            }
        ]
    }

    with patch("gateway.indexer.get_indexer_client", return_value=mock_indexer):
        logs = fetch_app_logs(100, 400)
        assert len(logs) == 1
        assert logs[0]["tx_id"] == "TX1"
        assert logs[0]["logs"] == ["bG9nMQ=="]

def test_sync_bounty_from_chain(db_session):
    from gateway.indexer import sync_bounty_from_chain
    from gateway.database import Bounty

    # 1. Bounty is None (standalone mode mock)
    with patch("gateway.indexer.Bounty", None):
        assert sync_bounty_from_chain(db_session, "b_1", "claimed") is None

    # 2. Bounty not found
    assert sync_bounty_from_chain(db_session, "b_missing", "claimed") is None

    # 3. Success update
    db_session.add(Bounty(bounty_id="b_sync", status="open", creator="C1", amount=1000, repo_url="r"))
    db_session.commit()

    updated = sync_bounty_from_chain(db_session, "b_sync", "claimed")
    assert updated is not None
    assert updated.status == "claimed"

    # 4. DB Exception during query
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("db error")
    assert sync_bounty_from_chain(mock_db, "b_sync", "claimed") is None

    # 5. DB Exception during commit
    mock_db2 = MagicMock()
    mock_bounty = MagicMock(status="open")
    mock_db2.query().filter().first.return_value = mock_bounty
    mock_db2.commit.side_effect = Exception("commit error")
    assert sync_bounty_from_chain(mock_db2, "b_sync", "claimed") is None

@patch("gateway.indexer.get_algod_client")
def test_get_bounty_app_info(mock_get_client):
    from gateway.indexer import get_bounty_app_info
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    assert get_bounty_app_info(None, None) is None
    assert get_bounty_app_info(None, 0) is None

    mock_client.application_info.return_value = {
        "last-round": 500,
        "params": {
            "approval-program": "app1"
        },
        "apps-local-state": {
            "box-entries": [
                {"name": "test_box", "value": "test_val"}
            ]
        }
    }

    info = get_bounty_app_info(None, 123)
    assert info["app_id"] == 123
    assert info["confirmed_round"] == 500
    assert info["approval_program"] == "app1"
    assert info["state"] == "escrow_active"
    assert info["box_test_box"] == "test_val"

    mock_client.application_info.side_effect = Exception("error")
    assert get_bounty_app_info(None, 123) is None


@patch("gateway.indexer.get_algod_client")
def test_read_box_value_invalid_hex(mock_get_client):
    from gateway.indexer import read_box_value
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.application_info.return_value = {
        "apps-local-state": {
            "box-entries": [
                {"name": "test_box", "value": "zzzz"} # Invalid hex
            ]
        }
    }

    val = read_box_value(12345, "test_box")
    assert val == "zzzz"

@patch("gateway.indexer.get_indexer_client")
def test_poll_bounty_events(mock_get_client):
    from gateway.indexer import poll_bounty_events

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.search_applications.return_value = {
        "current-round": 1000,
        "applications": [
            {"id": 0}, # skipped
            {"id": 123, "params": {"approval-program": "prog1"}}
        ]
    }

    events = poll_bounty_events()
    assert len(events) == 1
    assert events[0]["app_id"] == 123
    assert events[0]["app_status"] == "prog1"
    assert events[0]["round"] == 1000

    mock_client.search_applications.side_effect = Exception("error")
    assert poll_bounty_events() == []

    mock_get_client.side_effect = Exception("error")
    assert poll_bounty_events() == []
