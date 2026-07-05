import pytest
import asyncio
from unittest.mock import patch, MagicMock
from gateway.database import Bounty
from gateway.worker import indexer_worker
import signal

@pytest.mark.asyncio
async def test_worker_general_sync_valid_state(db_session, seeded_agents):
    bounty = Bounty(
        bounty_id="b_general",
        app_id=999,
        status="open",
        creator="CREATOR_ADDR",
        amount=10,
        asset_id=0,
        repo_url="https://github.com/test/test"
    )
    db_session.add(bounty)
    db_session.commit()

    mock_events = [{"app_id": 999, "round": 100}]

    # 2 -> "submitted"
    import struct
    mock_box_bytes = struct.pack('>Q', 2)

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=mock_events), \
         patch("gateway.worker.read_box_value", return_value=mock_box_bytes), \
         patch("gateway.worker.sync_bounty_from_chain") as mock_sync, \
         patch("gateway.worker.fetch_app_logs", return_value=[]), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

    mock_sync.assert_called_once_with(db_session, "b_general", "submitted")

@pytest.mark.asyncio
async def test_worker_general_sync_hex_string(db_session, seeded_agents):
    bounty = Bounty(
        bounty_id="b_general_hex",
        app_id=888,
        status="claimed",
        creator="CREATOR_ADDR",
        amount=10,
        asset_id=0,
        repo_url="https://github.com/test/test"
    )
    db_session.add(bounty)
    db_session.commit()

    mock_events = [{"app_id": 888, "round": 100}]

    # 5 -> "closed" in hex string
    mock_box_hex = "0000000000000005"

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=mock_events), \
         patch("gateway.worker.read_box_value", return_value=mock_box_hex), \
         patch("gateway.worker.sync_bounty_from_chain") as mock_sync, \
         patch("gateway.worker.fetch_app_logs", return_value=[]), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

    mock_sync.assert_called_once_with(db_session, "b_general_hex", "closed")

@pytest.mark.asyncio
async def test_worker_general_sync_invalid_hex(db_session, seeded_agents):
    bounty = Bounty(
        bounty_id="b_general_bad_hex",
        app_id=777,
        status="claimed",
        creator="CREATOR_ADDR",
        amount=10,
        asset_id=0,
        repo_url="https://github.com/test/test"
    )
    db_session.add(bounty)
    db_session.commit()

    mock_events = [{"app_id": 777, "round": 100}]

    # an invalid hex string that will be encoded to bytes
    mock_box_str = "not_a_hex_string"

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=mock_events), \
         patch("gateway.worker.read_box_value", return_value=mock_box_str), \
         patch("gateway.worker.sync_bounty_from_chain") as mock_sync, \
         patch("gateway.worker.fetch_app_logs", return_value=[]), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

    mock_sync.assert_not_called()

@pytest.mark.asyncio
async def test_worker_general_sync_exception(db_session, seeded_agents):
    bounty = Bounty(
        bounty_id="b_general_exception",
        app_id=666,
        status="claimed",
        creator="CREATOR_ADDR",
        amount=10,
        asset_id=0,
        repo_url="https://github.com/test/test"
    )
    db_session.add(bounty)
    db_session.commit()

    mock_events = [{"app_id": 666, "round": 100}]

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=mock_events), \
         patch("gateway.worker.read_box_value", side_effect=Exception("Test Error")), \
         patch("gateway.worker.sync_bounty_from_chain") as mock_sync, \
         patch("gateway.worker.fetch_app_logs", return_value=[]), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

    mock_sync.assert_not_called()

@pytest.mark.asyncio
async def test_worker_not_implemented_error(db_session, seeded_agents):
    # Tests the Windows fallback when add_signal_handler throws NotImplementedError
    mock_event = MagicMock()
    mock_event.is_set.side_effect = [True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    mock_loop = MagicMock()
    mock_loop.add_signal_handler.side_effect = NotImplementedError()

    with patch("gateway.worker.asyncio.get_running_loop", return_value=mock_loop), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event), \
         patch("gateway.worker.signal.signal"):
        await indexer_worker()

@pytest.mark.asyncio
async def test_worker_timeout(db_session, seeded_agents):
    # Test wait timeout coverage
    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        raise asyncio.TimeoutError()
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=[]), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

@pytest.mark.asyncio
async def test_worker_polling_error(db_session):
    # Test internal exception raised
    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", side_effect=Exception("DB Error")), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

@pytest.mark.asyncio
async def test_worker_fatal_error(db_session):
    # Test fatal exception raised inside worker outer loop
    with patch("gateway.worker.SessionLocal", side_effect=Exception("DB Error")) as mock_session, \
         patch("gateway.worker.poll_bounty_events", side_effect=Exception("Fatal Error")):
        # By patching something inside the `while not stop_event.is_set()` loop that is NOT caught
        # wait, polling error is caught by `except Exception as e: print("Polling error")`.
        # The fatal exception is caught by the outermost try/except block.
        # So we mock stop_event.is_set to raise an Exception.
        mock_event = MagicMock()
        mock_event.is_set.side_effect = Exception("Fatal Error")
        with patch("gateway.worker.asyncio.Event", return_value=mock_event):
            await indexer_worker()
@pytest.mark.asyncio
async def test_worker_continue_no_app_id(db_session, seeded_agents):
    bounty = Bounty(
        bounty_id="b_no_app_id",
        app_id=None,
        status="claimed",
        creator="CREATOR_ADDR",
        amount=10,
        asset_id=0,
        repo_url="https://github.com/test/test"
    )
    db_session.add(bounty)
    db_session.commit()

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs") as mock_fetch, \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

    mock_fetch.assert_not_called()
