import pytest
import base64
from unittest.mock import patch, MagicMock
from algosdk import account
from algosdk.encoding import decode_address
from gateway.database import Bounty, Evaluator, DisputeEvaluator
from gateway.worker import indexer_worker

@pytest.mark.asyncio
async def test_worker_dispute_submitted_evaluator_batch(db_session, seeded_agents):
    # Setup disputed bounty record
    bounty = Bounty(
        bounty_id="b_dispute_batch",
        app_id=12345,
        status="submitted",
        creator="CREATOR_ADDR",
        worker="WORKER_ADDR",
        amount=1000,
        repo_url="r"
    )
    db_session.add(bounty)
    db_session.commit()

    # Generate 3 valid evaluator addresses
    _, addr1 = account.generate_account()
    _, addr2 = account.generate_account()
    _, addr3 = account.generate_account()

    logs_b64 = [
        base64.b64encode(b"dispute_submitted").decode(),
        base64.b64encode(decode_address(addr1)).decode(),
        base64.b64encode(decode_address(addr2)).decode(),
        base64.b64encode(decode_address(addr3)).decode()
    ]

    mock_logs = [
        {
            "round": 300,
            "logs": logs_b64
        }
    ]

    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait():
        return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):

        await indexer_worker()

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_dispute_batch").first()
    assert bounty.status == "disputed"

    evaluators = db_session.query(Evaluator).filter(Evaluator.address.in_([addr1, addr2, addr3])).all()
    assert len(evaluators) == 3

    assignments = db_session.query(DisputeEvaluator).filter(DisputeEvaluator.bounty_id == "b_dispute_batch").all()
    assert len(assignments) == 3
    assigned_addrs = [a.evaluator_address for a in assignments]
    assert addr1 in assigned_addrs
    assert addr2 in assigned_addrs
    assert addr3 in assigned_addrs
