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
