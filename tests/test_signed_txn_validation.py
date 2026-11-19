import base64
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from algosdk import account, encoding
from algosdk.abi import Method
from algosdk.transaction import (
    ApplicationCallTxn,
    OnComplete,
    PaymentTxn,
    SuggestedParams,
)

from gateway import algod_client
from gateway.database import Agent, Bounty, DisputeEvaluator
from tests.conftest import get_auth_token

GENESIS_HASH = base64.b64encode(b"\x00" * 32).decode()
SP = SuggestedParams(fee=1000, first=1, last=1000, gh=GENESIS_HASH, flat_fee=True)

SELECTORS = {
    "claim": Method.from_signature("claim_bounty()void").get_selector(),
    "submit": Method.from_signature("submit_work(byte[],byte[])void").get_selector(),
    "approve": Method.from_signature("approve_work()void").get_selector(),
    "reject": Method.from_signature("reject_work(byte[])void").get_selector(),
    "dispute": Method.from_signature("submit_dispute(byte[])void").get_selector(),
}


def _make_signed_app_call(
    sk: str,
    sender: str,
    app_id: int,
    selector: bytes,
    on_complete: OnComplete = OnComplete.NoOpOC,
    rekey_to: str | None = None,
) -> str:
    txn = ApplicationCallTxn(
        sender=sender,
        sp=SP,
        index=app_id,
        on_complete=on_complete,
        app_args=[selector],
        rekey_to=rekey_to,
    )
    return encoding.msgpack_encode(txn.sign(sk))


def _make_signed_zero_pay(sk: str, sender: str) -> str:
    txn = PaymentTxn(sender=sender, sp=SP, receiver=sender, amt=0)
    return encoding.msgpack_encode(txn.sign(sk))


# ─── Unit tests for verify_and_send_app_call_txn ────────────────────────────


def test_verify_rejects_zero_algo_payment_txn():
    sk, addr = account.generate_account()
    b64 = _make_signed_zero_pay(sk, addr)
    with pytest.raises(ValueError, match="appl"):
        algod_client.verify_and_send_app_call_txn(b64, 100, addr, SELECTORS["claim"])


def test_verify_rejects_wrong_app_id():
    sk, addr = account.generate_account()
    b64 = _make_signed_app_call(sk, addr, 999, SELECTORS["claim"])
    with pytest.raises(ValueError, match="app_id"):
        algod_client.verify_and_send_app_call_txn(b64, 100, addr, SELECTORS["claim"])


def test_verify_rejects_wrong_sender():
    sk, addr = account.generate_account()
    _, other_addr = account.generate_account()
    b64 = _make_signed_app_call(sk, addr, 100, SELECTORS["claim"])
    with pytest.raises(ValueError, match="sender"):
        algod_client.verify_and_send_app_call_txn(b64, 100, other_addr, SELECTORS["claim"])


def test_verify_rejects_wrong_selector():
    sk, addr = account.generate_account()
    b64 = _make_signed_app_call(sk, addr, 100, SELECTORS["approve"])
    with pytest.raises(ValueError, match="selector"):
        algod_client.verify_and_send_app_call_txn(b64, 100, addr, SELECTORS["claim"])


def test_verify_rejects_non_noop_on_complete():
    sk, addr = account.generate_account()
    b64 = _make_signed_app_call(
        sk, addr, 100, SELECTORS["claim"], on_complete=OnComplete.OptInOC
    )
    with pytest.raises(ValueError, match="OnComplete"):
        algod_client.verify_and_send_app_call_txn(b64, 100, addr, SELECTORS["claim"])


def test_verify_rejects_rekey_to_set():
    sk, addr = account.generate_account()
    _, rekey_addr = account.generate_account()
    b64 = _make_signed_app_call(
        sk, addr, 100, SELECTORS["claim"], rekey_to=rekey_addr
    )
    with pytest.raises(ValueError, match="rekey_to"):
        algod_client.verify_and_send_app_call_txn(b64, 100, addr, SELECTORS["claim"])


def test_verify_rejects_unsigned_txn():
    _, addr = account.generate_account()
    txn = ApplicationCallTxn(
        sender=addr,
        sp=SP,
        index=100,
        on_complete=OnComplete.NoOpOC,
        app_args=[SELECTORS["claim"]],
    )
    b64 = encoding.msgpack_encode(txn)
    with pytest.raises(ValueError, match="SignedTransaction"):
        algod_client.verify_and_send_app_call_txn(b64, 100, addr, SELECTORS["claim"])


def test_verify_accepts_valid_app_call_txn():
    sk, addr = account.generate_account()
    b64 = _make_signed_app_call(sk, addr, 100, SELECTORS["claim"])

    mock_ac = MagicMock()
    mock_ac.send_raw_transaction.return_value = "TXID_VALID_100"

    with (
        patch("gateway.algod_client.get_algod_client", return_value=mock_ac),
        patch("algosdk.transaction.wait_for_confirmation", return_value={"confirmed-round": 42}) as mock_wait,
    ):
        tx_id = algod_client.verify_and_send_app_call_txn(
            b64, 100, addr, SELECTORS["claim"]
        )

    assert tx_id == "TXID_VALID_100"
    mock_ac.send_raw_transaction.assert_called_once()
    mock_wait.assert_called_once_with(mock_ac, "TXID_VALID_100", 4)


# ─── Endpoint integration tests (non-sandbox mode) ──────────────────────────


def _seed_wallets_and_bounty(db_session, status="open", app_id=555):
    c_sk, c_addr = account.generate_account()
    w_sk, w_addr = account.generate_account()
    creator = Agent(
        address=c_addr,
        karma=50,
        steward_name="Stew C",
        steward_email="c@example.com",
        steward_verified=True,
    )
    worker = Agent(
        address=w_addr,
        karma=50,
        steward_name="Stew W",
        steward_email="w@example.com",
        steward_verified=True,
    )
    bounty = Bounty(
        bounty_id="b_val_1",
        app_id=app_id,
        status=status,
        creator=c_addr,
        worker=w_addr if status != "open" else None,
        amount=10_000_000,
        repo_url="https://github.com/test/repo",
    )
    db_session.add_all([creator, worker, bounty])
    db_session.commit()
    return (c_sk, c_addr), (w_sk, w_addr), bounty


@pytest.mark.parametrize(
    "endpoint,initial_status,role,payload_extra",
    [
        ("/claim", "open", "worker", {}),
        ("/submit", "claimed", "worker", {"pr_url": "https://github.com/test/repo/pull/1"}),
        ("/approve", "submitted", "creator", {}),
        ("/reject", "submitted", "creator", {"reason": "incomplete"}),
        ("/dispute", "submitted", "worker", {"reason": "unfair"}),
    ],
)
def test_non_sandbox_rejects_zero_pay_txn(
    client, db_session, endpoint, initial_status, role, payload_extra
):
    (c_sk, c_addr), (w_sk, w_addr), _ = _seed_wallets_and_bounty(
        db_session, status=initial_status, app_id=555
    )
    sk, addr = (w_sk, w_addr) if role == "worker" else (c_sk, c_addr)
    token = get_auth_token(client, addr)

    payload = {**payload_extra, "signed_txn": _make_signed_zero_pay(sk, addr)}
    with patch("gateway.config.Config.ALGORAND_NETWORK", new_callable=PropertyMock, return_value="testnet"):
        res = client.post(
            f"/api/v1/bounties/b_val_1{endpoint}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 400
    assert "On-chain transaction failed" in res.json()["detail"]


@pytest.mark.parametrize(
    "endpoint,initial_status,role,payload_extra",
    [
        ("/reject", "submitted", "creator", {"reason": "incomplete"}),
        ("/dispute", "submitted", "worker", {"reason": "unfair"}),
    ],
)
def test_non_sandbox_rejects_omitted_signed_txn_on_reject_and_dispute(
    client, db_session, endpoint, initial_status, role, payload_extra
):
    (_, c_addr), (_, w_addr), _ = _seed_wallets_and_bounty(
        db_session, status=initial_status, app_id=555
    )
    addr = w_addr if role == "worker" else c_addr
    token = get_auth_token(client, addr)

    with patch("gateway.config.Config.ALGORAND_NETWORK", new_callable=PropertyMock, return_value="testnet"):
        res = client.post(
            f"/api/v1/bounties/b_val_1{endpoint}",
            json=payload_extra,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 400
    assert "signed_txn is required" in res.json()["detail"]


@pytest.mark.parametrize(
    "endpoint,action_key,initial_status,expected_status,role,payload_extra",
    [
        ("/claim", "claim", "open", "claimed", "worker", {}),
        ("/submit", "submit", "claimed", "submitted", "worker", {"pr_url": "https://github.com/test/repo/pull/1"}),
        ("/approve", "approve", "submitted", "closed", "creator", {}),
        ("/reject", "reject", "submitted", "rejected", "creator", {"reason": "needs tests"}),
        ("/dispute", "dispute", "submitted", "disputed", "worker", {"reason": "disagree"}),
    ],
)
def test_non_sandbox_accepts_valid_app_call_txn(
    client,
    db_session,
    endpoint,
    action_key,
    initial_status,
    expected_status,
    role,
    payload_extra,
):
    (c_sk, c_addr), (w_sk, w_addr), _ = _seed_wallets_and_bounty(
        db_session, status=initial_status, app_id=555
    )
    sk, addr = (w_sk, w_addr) if role == "worker" else (c_sk, c_addr)
    token = get_auth_token(client, addr)

    signed_b64 = _make_signed_app_call(sk, addr, 555, SELECTORS[action_key])
    mock_ac = MagicMock()
    mock_ac.send_raw_transaction.return_value = f"TXID_{action_key.upper()}"

    with (
        patch("gateway.config.Config.ALGORAND_NETWORK", new_callable=PropertyMock, return_value="testnet"),
        patch("gateway.algod_client.get_algod_client", return_value=mock_ac),
        patch("algosdk.transaction.wait_for_confirmation", return_value={"confirmed-round": 10}),
    ):
        res = client.post(
            f"/api/v1/bounties/b_val_1{endpoint}",
            json={**payload_extra, "signed_txn": signed_b64},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == expected_status
    assert body["tx_id"] == f"TXID_{action_key.upper()}"
    mock_ac.send_raw_transaction.assert_called_once()


# ─── Bounty creation (create_bounty) signed_txn validation ──────────────────

CREATE_SELECTOR = Method.from_signature(
    "create_bounty(byte[],uint64,uint64,uint64,uint64,address,address,address,uint64)void"
).get_selector()


def test_create_bounty_verify_rejects_zero_pay():
    sk, addr = account.generate_account()
    pay_b64 = _make_signed_zero_pay(sk, addr)
    with pytest.raises(ValueError, match="appl"):
        algod_client.verify_and_send_bounty_creation_txns(pay_b64, 555, addr, CREATE_SELECTOR)


def test_create_bounty_verify_rejects_rekey_in_group():
    sk, addr = account.generate_account()
    _, target = account.generate_account()
    pay_txn = PaymentTxn(sender=addr, sp=SP, receiver=addr, amt=0, rekey_to=target)
    pay_b64 = encoding.msgpack_encode(pay_txn.sign(sk))
    app_b64 = _make_signed_app_call(sk, addr, 555, CREATE_SELECTOR)
    with pytest.raises(ValueError, match="rekey_to"):
        algod_client.verify_and_send_bounty_creation_txns(
            f"{pay_b64},{app_b64}", 555, addr, CREATE_SELECTOR
        )


def test_create_bounty_verify_accepts_valid_group():
    sk, addr = account.generate_account()
    pay_b64 = _make_signed_zero_pay(sk, addr)
    app_b64 = _make_signed_app_call(sk, addr, 555, CREATE_SELECTOR)

    mock_ac = MagicMock()
    mock_ac.send_transactions.return_value = "TXID_GROUP_CREATE"

    with (
        patch("gateway.algod_client.get_algod_client", return_value=mock_ac),
        patch("algosdk.transaction.wait_for_confirmation", return_value={"confirmed-round": 12}),
    ):
        tx_id = algod_client.verify_and_send_bounty_creation_txns(
            f"{pay_b64},{app_b64}", 555, addr, CREATE_SELECTOR
        )

    assert tx_id == "TXID_GROUP_CREATE"
    mock_ac.send_transactions.assert_called_once()


def test_create_bounty_endpoint_rejects_spoofed_txn_when_non_sandbox(client, db_session):
    c_sk, c_addr = account.generate_account()
    db_session.add(
        Agent(
            address=c_addr,
            karma=50,
            steward_name="Stew C",
            steward_email="c@example.com",
            steward_verified=True,
        )
    )
    db_session.commit()

    token = get_auth_token(client, c_addr)
    spoof_b64 = _make_signed_zero_pay(c_sk, c_addr)
    mock_ac = MagicMock()

    with (
        patch("gateway.routers.bounties.sandbox_active", False),
        patch("gateway.algod_client.get_algod_client", return_value=mock_ac),
    ):
        res = client.post(
            "/api/v1/bounties",
            json={
                "description": "Test bounty",
                "repo_url": "https://github.com/IcanBENCHurCAT/algo-bounty",
                "issue_number": 999,
                "amount": 1000000,
                "app_id": 555,
                "signed_txn": spoof_b64,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 400, res.text
    mock_ac.send_raw_transaction.assert_not_called()
    mock_ac.send_transactions.assert_not_called()


# ─── Dispute vote (vote_dispute) signed_txn validation ───────────────────────

VOTE_DISPUTE_SELECTOR = Method.from_signature("vote_dispute(uint64)void").get_selector()


def _seed_dispute_vote(db_session, app_id=555):
    _seed_wallets_and_bounty(db_session, status="disputed", app_id=app_id)
    ev_sk, ev_addr = account.generate_account()
    db_session.add(Agent(address=ev_addr, karma=80))
    db_session.add(DisputeEvaluator(bounty_id="b_val_1", evaluator_address=ev_addr))
    db_session.commit()
    return ev_sk, ev_addr


def test_vote_dispute_non_sandbox_rejects_missing_app_id(client, db_session):
    ev_sk, ev_addr = _seed_dispute_vote(db_session, app_id=None)
    token = get_auth_token(client, ev_addr)
    signed_b64 = _make_signed_app_call(ev_sk, ev_addr, 555, VOTE_DISPUTE_SELECTOR)
    mock_ac = MagicMock()

    with (
        patch("gateway.config.Config.ALGORAND_NETWORK", new_callable=PropertyMock, return_value="testnet"),
        patch("gateway.algod_client.get_algod_client", return_value=mock_ac),
    ):
        res = client.post(
            "/api/v1/evaluators/bounties/b_val_1/vote",
            json={"vote": "worker", "signed_txn": signed_b64},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 400
    assert "no on-chain app_id" in res.json()["detail"]
    assignment = db_session.query(DisputeEvaluator).filter_by(bounty_id="b_val_1", evaluator_address=ev_addr).first()
    assert assignment.vote is None
    mock_ac.send_raw_transaction.assert_not_called()


@pytest.mark.parametrize("bad_case", ["zero_pay", "wrong_app_id", "wrong_sender", "rekey_to", "wrong_selector"])
def test_vote_dispute_non_sandbox_rejects_invalid_txn(client, db_session, bad_case):
    ev_sk, ev_addr = _seed_dispute_vote(db_session, app_id=555)
    token = get_auth_token(client, ev_addr)
    other_sk, other_addr = account.generate_account()

    if bad_case == "zero_pay":
        signed_b64 = _make_signed_zero_pay(ev_sk, ev_addr)
    elif bad_case == "wrong_app_id":
        signed_b64 = _make_signed_app_call(ev_sk, ev_addr, 999, VOTE_DISPUTE_SELECTOR)
    elif bad_case == "wrong_sender":
        signed_b64 = _make_signed_app_call(other_sk, other_addr, 555, VOTE_DISPUTE_SELECTOR)
    elif bad_case == "rekey_to":
        signed_b64 = _make_signed_app_call(ev_sk, ev_addr, 555, VOTE_DISPUTE_SELECTOR, rekey_to=other_addr)
    else:
        signed_b64 = _make_signed_app_call(ev_sk, ev_addr, 555, SELECTORS["approve"])

    mock_ac = MagicMock()
    with (
        patch("gateway.config.Config.ALGORAND_NETWORK", new_callable=PropertyMock, return_value="testnet"),
        patch("gateway.algod_client.get_algod_client", return_value=mock_ac),
    ):
        res = client.post(
            "/api/v1/evaluators/bounties/b_val_1/vote",
            json={"vote": "worker", "signed_txn": signed_b64},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 400
    assert "On-chain transaction failed" in res.json()["detail"]
    assignment = db_session.query(DisputeEvaluator).filter_by(bounty_id="b_val_1", evaluator_address=ev_addr).first()
    assert assignment.vote is None
    mock_ac.send_raw_transaction.assert_not_called()


def test_vote_dispute_non_sandbox_accepts_valid_app_call_txn(client, db_session):
    ev_sk, ev_addr = _seed_dispute_vote(db_session, app_id=555)
    token = get_auth_token(client, ev_addr)
    signed_b64 = _make_signed_app_call(ev_sk, ev_addr, 555, VOTE_DISPUTE_SELECTOR)

    mock_ac = MagicMock()
    mock_ac.send_raw_transaction.return_value = "TXID_VOTE_DISPUTE"

    with (
        patch("gateway.config.Config.ALGORAND_NETWORK", new_callable=PropertyMock, return_value="testnet"),
        patch("gateway.algod_client.get_algod_client", return_value=mock_ac),
        patch("algosdk.transaction.wait_for_confirmation", return_value={"confirmed-round": 15}),
    ):
        res = client.post(
            "/api/v1/evaluators/bounties/b_val_1/vote",
            json={"vote": "worker", "signed_txn": signed_b64},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "voted"
    assert body["vote"] == "worker"
    assert body["tx_id"] == "TXID_VOTE_DISPUTE"
    db_session.expire_all()
    assignment = db_session.query(DisputeEvaluator).filter_by(bounty_id="b_val_1", evaluator_address=ev_addr).first()
    assert assignment.vote == "worker"
    mock_ac.send_raw_transaction.assert_called_once()
