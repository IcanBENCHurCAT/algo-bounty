import pytest
from unittest.mock import patch
from gateway.database import Agent, Arbitrator, Bounty, DisputeArbitrator
from tests.conftest import get_auth_token

def test_arbitrator_registration_insufficient_karma(client, db_session):
    # Create agent with low karma
    agent = Agent(address="LOW_KARMA_ARB", karma=10)
    db_session.add(agent)
    db_session.commit()

    token = get_auth_token(client, "LOW_KARMA_ARB")
    res = client.post(
        "/api/v1/arbitrators/register",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403
    assert "Insufficient karma" in res.json()["detail"]

def test_arbitrator_registration_success(client, db_session):
    # Create agent with high karma
    agent = Agent(address="HIGH_KARMA_ARB", karma=60)
    db_session.add(agent)
    db_session.commit()

    token = get_auth_token(client, "HIGH_KARMA_ARB")
    res = client.post(
        "/api/v1/arbitrators/register",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "registered"

    # Verify db record
    arb = db_session.query(Arbitrator).filter(Arbitrator.address == "HIGH_KARMA_ARB").first()
    assert arb is not None
    assert arb.status == "active"

    # Deregister
    res_dereg = client.post(
        "/api/v1/arbitrators/deregister",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_dereg.status_code == 200
    assert res_dereg.json()["status"] == "deregistered"

    # Verify status changed in db
    db_session.refresh(arb)
    assert arb.status == "inactive"

def test_arbitrator_voting_restrictions(client, db_session):
    # Seed agents and a disputed bounty
    creator = Agent(address="CREATOR_ADDR", karma=50)
    worker = Agent(address="WORKER_ADDR", karma=50)
    arb = Agent(address="ARB_ADDR", karma=60)
    bounty = Bounty(bounty_id="b_dispute", status="disputed", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r")
    
    db_session.add_all([creator, worker, arb, bounty])
    db_session.commit()

    # Case 1: Unassigned arbitrator votes
    arb_token = get_auth_token(client, "ARB_ADDR")
    res = client.post(
        "/api/v1/arbitrators/bounties/b_dispute/vote",
        json={"vote": "worker"},
        headers={"Authorization": f"Bearer {arb_token}"}
    )
    assert res.status_code == 403
    assert "You are not assigned" in res.json()["detail"]

    # Case 2: Assigned arbitrator votes
    assignment = DisputeArbitrator(bounty_id="b_dispute", arbitrator_address="ARB_ADDR")
    db_session.add(assignment)
    db_session.commit()

    res_vote = client.post(
        "/api/v1/arbitrators/bounties/b_dispute/vote",
        json={"vote": "worker"},
        headers={"Authorization": f"Bearer {arb_token}"}
    )
    assert res_vote.status_code == 200
    assert res_vote.json()["status"] == "voted"
    assert res_vote.json()["vote"] == "worker"

    # Case 3: Assigned arbitrator attempts to vote again
    res_vote_again = client.post(
        "/api/v1/arbitrators/bounties/b_dispute/vote",
        json={"vote": "split"},
        headers={"Authorization": f"Bearer {arb_token}"}
    )
    assert res_vote_again.status_code == 400
    assert "already cast your vote" in res_vote_again.json()["detail"]


@pytest.mark.asyncio
async def test_worker_dispute_submitted_and_voted(db_session, seeded_agents):
    import base64
    from unittest.mock import patch, MagicMock
    from algosdk import account
    from algosdk.encoding import decode_address
    from gateway.worker import indexer_worker

    # Setup disputed bounty record
    bounty = Bounty(
        bounty_id="b_dispute_worker",
        app_id=789,
        status="submitted",
        creator="CREATOR_ADDR",
        worker="WORKER_ADDR",
        amount=1000,
        repo_url="r"
    )
    db_session.add(bounty)
    db_session.commit()

    # Generate 3 valid arbitrator addresses
    _, addr1 = account.generate_account()
    _, addr2 = account.generate_account()
    _, addr3 = account.generate_account()

    # Encode addresses to bytes, then base64 for app logs
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

    # Assert db changes
    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_dispute_worker").first()
    assert bounty.status == "disputed"

    assignments = db_session.query(DisputeArbitrator).filter(DisputeArbitrator.bounty_id == "b_dispute_worker").all()
    assert len(assignments) == 3
    assigned_addrs = [a.arbitrator_address for a in assignments]
    assert addr1 in assigned_addrs
    assert addr2 in assigned_addrs
    assert addr3 in assigned_addrs

    # Now simulate arbitrator 1 voting
    import struct
    vote_val_bytes = struct.pack('>Q', 1) # Option 1: Worker
    vote_logs_b64 = [
        base64.b64encode(b"arbitrator_voted").decode(),
        base64.b64encode(decode_address(addr1)).decode(),
        base64.b64encode(vote_val_bytes).decode()
    ]

    mock_vote_logs = [
        {
            "round": 301,
            "logs": vote_logs_b64
        }
    ]

    mock_event2 = MagicMock()
    mock_event2.is_set.side_effect = [False, True]
    mock_event2.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=mock_vote_logs), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event2):

        await indexer_worker()

    # Assert arbitrator vote is recorded
    vote_record = db_session.query(DisputeArbitrator).filter(
        DisputeArbitrator.bounty_id == "b_dispute_worker",
        DisputeArbitrator.arbitrator_address == addr1
    ).first()
    assert vote_record.vote == "worker"
    assert vote_record.voted_at is not None


@pytest.mark.asyncio
async def test_worker_dispute_resolved_agent_win(db_session, seeded_agents):
    from unittest.mock import patch, MagicMock
    import base64
    from gateway.worker import indexer_worker

    # Seed bounty
    bounty = Bounty(bounty_id="b_outcome_worker", app_id=101, status="disputed", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r")
    db_session.add(bounty)
    db_session.commit()

    mock_logs = [{"round": 401, "logs": [base64.b64encode(b"dispute_resolved_agent_win").decode()]}]
    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait(): return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):
        await indexer_worker()

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_outcome_worker").first()
    assert bounty.status == "closed"
    assert bounty.payout_type == "PAYOUT"

    worker = db_session.query(Agent).filter(Agent.address == "WORKER_ADDR").first()
    creator = db_session.query(Agent).filter(Agent.address == "CREATOR_ADDR").first()
    assert worker.karma == 35 # 30 + 5
    assert worker.completed_bounties == 1
    assert creator.karma == 45 # 50 - 5
    assert creator.disputes_lost == 1


@pytest.mark.asyncio
async def test_worker_dispute_resolved_creator_win(db_session, seeded_agents):
    from unittest.mock import patch, MagicMock
    import base64
    from gateway.worker import indexer_worker

    bounty = Bounty(bounty_id="b_outcome_creator", app_id=102, status="disputed", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r")
    db_session.add(bounty)
    db_session.commit()

    mock_logs = [{"round": 402, "logs": [base64.b64encode(b"dispute_resolved_creator_win").decode()]}]
    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait(): return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):
        await indexer_worker()

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_outcome_creator").first()
    assert bounty.status == "closed"
    assert bounty.payout_type == "REFUND"

    worker = db_session.query(Agent).filter(Agent.address == "WORKER_ADDR").first()
    creator = db_session.query(Agent).filter(Agent.address == "CREATOR_ADDR").first()
    assert worker.karma == 25 # 30 - 5
    assert worker.disputes_lost == 1
    assert creator.karma == 55 # 50 + 5


@pytest.mark.asyncio
async def test_worker_dispute_resolved_split(db_session, seeded_agents):
    from unittest.mock import patch, MagicMock
    import base64
    from gateway.worker import indexer_worker

    bounty = Bounty(bounty_id="b_outcome_split", app_id=103, status="disputed", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r")
    db_session.add(bounty)
    db_session.commit()

    mock_logs = [{"round": 403, "logs": [base64.b64encode(b"dispute_resolved_split").decode()]}]
    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True]
    async def mock_wait(): return True
    mock_event.wait = mock_wait

    with patch("gateway.worker.SessionLocal", return_value=db_session), \
         patch("gateway.worker.poll_bounty_events", return_value=[]), \
         patch("gateway.worker.fetch_app_logs", return_value=mock_logs), \
         patch("gateway.worker.asyncio.Event", return_value=mock_event):
        await indexer_worker()

    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == "b_outcome_split").first()
    assert bounty.status == "closed"
    assert bounty.payout_type == "SPLIT"

    worker = db_session.query(Agent).filter(Agent.address == "WORKER_ADDR").first()
    creator = db_session.query(Agent).filter(Agent.address == "CREATOR_ADDR").first()
    assert worker.karma == 30 # no change
    assert worker.completed_bounties == 1
    assert creator.karma == 50 # no change


def test_inactive_arbitrator_penalised(db_session):
    """T024 - Arbitrators who miss the voting deadline get -5 karma and vote='abstained'."""
    from datetime import datetime, timezone, timedelta
    from gateway.worker import check_inactive_arbitrators, ARBITRATOR_VOTE_DEADLINE_HOURS

    # Create a disputed bounty
    bounty = Bounty(
        bounty_id="b_inactive_arb",
        app_id=999,
        status="disputed",
        creator="CREATOR_INACTIVE",
        worker="WORKER_INACTIVE",
        amount=5000,
        repo_url="r"
    )
    # Create the arbitrator agent
    arb_agent = Agent(address="INACTIVE_ARB", karma=60)
    # Register the arbitrator with a timestamp older than the deadline
    old_time = datetime.now(timezone.utc) - timedelta(hours=ARBITRATOR_VOTE_DEADLINE_HOURS + 1)
    arb_row = Arbitrator(address="INACTIVE_ARB", status="active", registered_at=old_time)
    # Assign but no vote yet
    assignment = DisputeArbitrator(bounty_id="b_inactive_arb", arbitrator_address="INACTIVE_ARB")

    db_session.add_all([bounty, arb_agent, arb_row, assignment])
    db_session.commit()

    changes = check_inactive_arbitrators(db_session)
    db_session.commit()

    assert changes is True

    # Assignment should be marked abstained
    updated = db_session.query(DisputeArbitrator).filter(
        DisputeArbitrator.bounty_id == "b_inactive_arb",
        DisputeArbitrator.arbitrator_address == "INACTIVE_ARB"
    ).first()
    assert updated.vote == "abstained"
    assert updated.voted_at is not None

    # Karma should be reduced by 5
    updated_agent = db_session.query(Agent).filter(Agent.address == "INACTIVE_ARB").first()
    assert updated_agent.karma == 55  # 60 - 5


def test_active_arbitrator_not_penalised(db_session):
    """T024 - Arbitrators registered AFTER the cutoff should NOT be penalised yet."""
    from datetime import datetime, timezone
    from gateway.worker import check_inactive_arbitrators

    bounty = Bounty(
        bounty_id="b_active_arb",
        app_id=998,
        status="disputed",
        creator="CREATOR_ACTIVE",
        worker="WORKER_ACTIVE",
        amount=5000,
        repo_url="r"
    )
    arb_agent = Agent(address="ACTIVE_ARB", karma=60)
    # Registered just now — well within the 48h window
    arb_row = Arbitrator(address="ACTIVE_ARB", status="active", registered_at=datetime.now(timezone.utc))
    assignment = DisputeArbitrator(bounty_id="b_active_arb", arbitrator_address="ACTIVE_ARB")

    db_session.add_all([bounty, arb_agent, arb_row, assignment])
    db_session.commit()

    changes = check_inactive_arbitrators(db_session)

    assert changes is False

    updated_agent = db_session.query(Agent).filter(Agent.address == "ACTIVE_ARB").first()
    assert updated_agent.karma == 60  # no penalty
