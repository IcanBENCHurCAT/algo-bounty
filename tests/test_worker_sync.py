import pytest
import asyncio
import base64
from unittest.mock import patch, MagicMock
from gateway.database import Agent, Bounty
from gateway.worker import indexer_worker



@pytest.mark.asyncio
async def test_worker_hitm_auto_release(db_session, seeded_agents):
    bounty = Bounty(
        bounty_id="b_hitm",
        app_id=123,
        status="submitted",
        creator="CREATOR_ADDR",
        worker="WORKER_ADDR",
        amount=10,
        asset_id=0,
        is_hitm=True,
        repo_url="https://github.com/test/test"
    )
    db_session.add(bounty)
    db_session.commit()

    mock_logs = [
        {
            "round": 100,
            "logs": [base64.b64encode(b"auto_released_hitm").decode()]
        }
    ]

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("asyncio.wait_for", side_effect=asyncio.CancelledError): # To stop the loop

        try:
            await indexer_worker()
        except asyncio.CancelledError:
            pass

    # Fetch from DB again instead of refreshing stale object if it was detached
    b = db_session.query(Bounty).filter(Bounty.bounty_id == "b_hitm").first()
    assert b.status == "closed"
    assert b.payout_type == "PAYOUT"

    worker = db_session.query(Agent).filter(Agent.address == "WORKER_ADDR").first()
    creator = db_session.query(Agent).filter(Agent.address == "CREATOR_ADDR").first()
    assert worker.karma == 33 # 30 + 3
    assert creator.karma == 52 # 50 + 2

@pytest.mark.asyncio
async def test_worker_claim_expired(db_session, seeded_agents):
    bounty = Bounty(
        bounty_id="b_expired",
        app_id=456,
        status="claimed",
        creator="CREATOR_ADDR",
        worker="WORKER_ADDR",
        amount=10,
        asset_id=0,
        repo_url="https://github.com/test/test"
    )
    db_session.add(bounty)
    db_session.commit()

    mock_logs = [
        {
            "round": 200,
            "logs": [base64.b64encode(b"claim_expired").decode()]
        }
    ]

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("asyncio.wait_for", side_effect=asyncio.CancelledError):

        try:
            await indexer_worker()
        except asyncio.CancelledError:
            pass

    b = db_session.query(Bounty).filter(Bounty.bounty_id == "b_expired").first()
    assert b.status == "open"
    assert b.worker is None

    worker = db_session.query(Agent).filter(Agent.address == "WORKER_ADDR").first()
    assert worker.karma == 10 # 30 - 20
