import pytest
from unittest.mock import patch, MagicMock
from gateway.database import Bounty, Agent

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

def test_create_bounty_missing_agent(client):
    from gateway.auth import create_jwt_token
    token = create_jwt_token("STRANGER_ADDR")
    # Agent doesn't exist in DB yet, but verify creates it.
    # To test missing agent profile, we mock get_current_user to return a missing agent address but db query returns None.
    with patch("gateway.routers.bounties.get_current_user", return_value="STRANGER_ADDR"):
        res2 = client.post("/api/v1/bounties", json={"description": "desc", "amount": 1000, "repo_url": "r"}, headers={"Authorization": f"Bearer {token}"})
        assert res2.status_code == 403
        assert "Agent profile missing" in res2.json()["detail"]

def test_bounties_router_error_cases(client, db_session, seeded_agents):
    from tests.conftest import get_auth_token
    creator, worker, low_karma = seeded_agents

    # 1. Claim bounty with insufficient karma
    # Seed a bounty with high karma requirement
    db_session.add(Bounty(bounty_id="b_high_karma", status="open", creator="CREATOR_ADDR", amount=1000, repo_url="r", karma_requirement=100))
    db_session.commit()
    
    low_karma_token = get_auth_token(client, "LOW_KARMA_WORKER")
    res = client.post("/api/v1/bounties/b_high_karma/claim", json={"signed_txn": "dummy"}, headers={"Authorization": f"Bearer {low_karma_token}"})
    assert res.status_code == 403
    assert "Insufficient karma" in res.json()["detail"]

    # 2. Claim missing bounty
    worker_token = get_auth_token(client, "WORKER_ADDR")
    res = client.post("/api/v1/bounties/b_missing/claim", json={"signed_txn": "dummy"}, headers={"Authorization": f"Bearer {worker_token}"})
    assert res.status_code == 404

    # Seed some bounties
    db_session.add(Bounty(bounty_id="b_open", status="open", creator="CREATOR_ADDR", amount=1000, repo_url="r"))
    db_session.add(Bounty(bounty_id="b_claimed", status="claimed", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r"))
    db_session.add(Bounty(bounty_id="b_submitted", status="submitted", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r"))
    db_session.add(Bounty(bounty_id="b_closed", status="closed", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r"))
    db_session.commit()

    # 3. Creator claims own bounty
    creator_token = get_auth_token(client, "CREATOR_ADDR")
    res = client.post("/api/v1/bounties/b_open/claim", json={"signed_txn": "dummy"}, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 400
    assert "Cannot claim your own bounty" in res.json()["detail"]

    # 4. Claim non-open bounty
    res = client.post("/api/v1/bounties/b_claimed/claim", json={"signed_txn": "dummy"}, headers={"Authorization": f"Bearer {worker_token}"})
    assert res.status_code == 400
    assert "not claimable" in res.json()["detail"]

    # 5. Submit work for non-claimed bounty
    res = client.post("/api/v1/bounties/b_open/submit", json={"pr_url": "http://pr", "proof_data": {}}, headers={"Authorization": f"Bearer {worker_token}"})
    assert res.status_code == 400
    assert "must be claimed" in res.json()["detail"]

    # 6. Submit work by non-assigned worker
    stranger_token = get_auth_token(client, "LOW_KARMA_WORKER")
    res = client.post("/api/v1/bounties/b_claimed/submit", json={"pr_url": "http://pr", "proof_data": {}}, headers={"Authorization": f"Bearer {stranger_token}"})
    assert res.status_code == 403
    assert "Only the claiming worker" in res.json()["detail"]

    # 7. Approve work for non-submitted bounty
    res = client.post("/api/v1/bounties/b_claimed/approve", json={}, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 400
    assert "no work submitted" in res.json()["detail"]

    # 8. Approve work by non-creator
    res = client.post("/api/v1/bounties/b_submitted/approve", json={}, headers={"Authorization": f"Bearer {worker_token}"})
    assert res.status_code == 403
    assert "Only creator can approve" in res.json()["detail"]

    # 9. Reject work for non-submitted bounty
    res = client.post("/api/v1/bounties/b_claimed/reject", json={"reason": "bad"}, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 400
    assert "No work submitted to reject" in res.json()["detail"]

    # 10. Reject work by non-creator
    res = client.post("/api/v1/bounties/b_submitted/reject", json={"reason": "bad"}, headers={"Authorization": f"Bearer {worker_token}"})
    assert res.status_code == 403
    assert "Only creator can reject" in res.json()["detail"]

    # 11. Dispute for non-submitted/rejected bounty
    res = client.post("/api/v1/bounties/b_open/dispute", json={"reason": "bad"}, headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 400
    assert "Cannot dispute at this stage" in res.json()["detail"]

    # 12. Dispute by non-participant
    res = client.post("/api/v1/bounties/b_submitted/dispute", json={"reason": "bad"}, headers={"Authorization": f"Bearer {stranger_token}"})
    assert res.status_code == 403
    assert "Only bounty participants can open a dispute" in res.json()["detail"]


def test_get_txn_endpoints_missing_app_id(client, db_session, seeded_agents):
    from tests.conftest import get_auth_token
    creator, worker, low_karma = seeded_agents

    # Seed bounty with app_id = None
    db_session.add(Bounty(bounty_id="b_null_app", status="open", creator="CREATOR_ADDR", amount=1000, repo_url="r", app_id=None))
    db_session.add(Bounty(bounty_id="b_submitted_null_app", status="submitted", creator="CREATOR_ADDR", worker="WORKER_ADDR", amount=1000, repo_url="r", app_id=None))
    db_session.commit()

    # Test claim txn missing app_id
    worker_token = get_auth_token(client, "WORKER_ADDR")
    res = client.post("/api/v1/bounties/b_null_app/claim/txn", headers={"Authorization": f"Bearer {worker_token}"})
    assert res.status_code == 400
    assert "Bounty has no deployed smart contract application ID" in res.json()["detail"]

    # Test approve txn missing app_id
    creator_token = get_auth_token(client, "CREATOR_ADDR")
    res = client.post("/api/v1/bounties/b_submitted_null_app/approve/txn", headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 400
    assert "Bounty has no deployed smart contract application ID" in res.json()["detail"]


def test_create_bounty_custom_treasury_deduction(client, db_session, seeded_agents):
    from tests.conftest import get_auth_token
    import algosdk
    from algosdk.abi import Method, ABIType
    from algosdk.transaction import ApplicationNoOpTxn, SignedTransaction, SuggestedParams
    from unittest.mock import patch, MagicMock
    
    creator, worker, low_karma = seeded_agents
    creator_token = get_auth_token(client, "CREATOR_ADDR")
    
    # 1. Seed pending bounty
    db_session.add(Bounty(
        bounty_id="b_custom_t",
        app_id=123,
        status="pending_deploy",
        creator="CREATOR_ADDR",
        amount=1000,
        repo_url="https://github.com/test/test"
    ))
    db_session.commit()
    
    mock_decode_map = {
        "CREATOR_ADDR": b"\x01" * 32,
        "WORKER_ADDR": b"\x02" * 32,
    }
    
    from unittest.mock import PropertyMock

    with patch("algosdk.encoding.decode_address", side_effect=lambda x: mock_decode_map.get(x, b"\x00" * 32)), \
         patch("algosdk.encoding.encode_address", side_effect=lambda x: "CREATOR_ADDR" if x == b"\x01" * 32 else "WORKER_ADDR"), \
         patch("gateway.config.Config.TREASURY_ADDRESS", new_callable=PropertyMock, return_value="CREATOR_ADDR"):
         
        # 2. Build custom treasury transaction
        method = Method.from_signature("create_bounty(byte[],uint64,uint64,uint64,uint64,address,address)void")
        selector = method.get_selector()
        
        b_id = ABIType.from_string("byte[]").encode(b"b_custom_t")
        amt = ABIType.from_string("uint64").encode(1000)
        hitm = ABIType.from_string("uint64").encode(0)
        asset = ABIType.from_string("uint64").encode(0)
        days = ABIType.from_string("uint64").encode(7)
        med = algosdk.encoding.decode_address("CREATOR_ADDR")
        custom_treasury = algosdk.encoding.decode_address("WORKER_ADDR") # different treasury
        
        app_args = [selector, b_id, amt, hitm, asset, days, med, custom_treasury]
        params = SuggestedParams(fee=1000, first=1, last=100, gh="Z2VuZXNpc19oYXNoXzMyX2J5dGVzX2xvbmdfcGFkZGVk")
        
        txn = ApplicationNoOpTxn(
            sender="CREATOR_ADDR",
            sp=params,
            index=123,
            app_args=app_args
        )
        stxn = SignedTransaction(txn, "dummy_sig")
        serialized = algosdk.encoding.msgpack_encode(stxn)
        
        # Verify creator karma starts at 50
        creator_agent = db_session.query(Agent).filter(Agent.address == "CREATOR_ADDR").first()
        assert creator_agent.karma == 50
        
        res = client.post("/api/v1/bounties", json={
            "description": "Test Custom Treasury",
            "amount": 1000,
            "repo_url": "https://github.com/test/test",
            "signed_txn": serialized,
            "bounty_id": "b_custom_t",
            "app_id": 123
        }, headers={"Authorization": f"Bearer {creator_token}"})
        
        assert res.status_code == 200
        
        # Verify 5 karma was deducted instead of 1
        db_session.refresh(creator_agent)
        assert creator_agent.karma == 45


def test_create_bounty_fee_validation(client, seeded_agents):
    _, _, _ = seeded_agents
    from tests.conftest import get_auth_token
    token = get_auth_token(client, "CREATOR_ADDR")
    
    res = client.post("/api/v1/bounties", json={
        "description": "Too high fee",
        "amount": 1000000,
        "repo_url": "https://github.com/test/repo",
        "platform_fee": 1200
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    assert "Platform fee cannot exceed 10%" in res.json()["detail"]


def test_bounty_fee_breakdown_dynamic(client, db_session, seeded_agents):
    _, _, _ = seeded_agents
    
    mock_decode_map = {
        "CREATOR_ADDR": b"\x01" * 32,
        "WORKER_ADDR": b"\x02" * 32,
    }
    
    with patch("algosdk.encoding.decode_address", side_effect=lambda x: mock_decode_map.get(x, b"\x00" * 32)), \
         patch("algosdk.encoding.encode_address", side_effect=lambda x: "CREATOR_ADDR" if x == b"\x01" * 32 else "WORKER_ADDR"):
         
        b = Bounty(
            bounty_id="b_dynamic_fee",
            app_id=98765,
            status="open",
            creator="CREATOR_ADDR",
            amount=1_000_000,
            repo_url="https://github.com/test/repo",
            platform_fee=500,
            treasury_address="GD64GE2CO655KJZTNST75T4UR24B54IGNST4O73VQQ375S45T4U4VQQ37Y"
        )
        db_session.add(b)
        db_session.commit()
        
        from tests.conftest import get_auth_token
        token = get_auth_token(client, "WORKER_ADDR")
        
        res = client.post("/api/v1/bounties/b_dynamic_fee/claim/txn", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        
        data = res.json()
        fb = data["fee_breakdown"]
        
        assert fb["developer_royalty"] == 25000
        assert fb["platform_treasury"] == 25000
        assert fb["mediator_fee"] == 0
        assert fb["claimant_payout"] == 950000




