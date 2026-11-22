from unittest.mock import PropertyMock, patch
import pytest

from gateway.config import settings
from gateway.database import Agent, CollateralDeposit, Vouch
from tests.conftest import get_auth_token


ADMIN_ADDR = "ADMIN_COLDSTART_ADDR"
VOUCHER_ADDR = "ELITE_VOUCHER_ADDR"
VOUCHED_ADDR = "NEWCOMER_VOUCHED_ADDR"
ATTACKER_ADDR = "ATTACKER_COLDSTART_ADDR"
DEPOSITOR_ADDR = "DEPOSITOR_COLDSTART_ADDR"


@pytest.fixture(autouse=True)
def clean_coldstart_tables(db_session):
    """Ensure cold-start tables are clean before and after each test."""
    db_session.query(CollateralDeposit).delete()
    db_session.query(Vouch).delete()
    db_session.commit()
    yield
    db_session.query(CollateralDeposit).delete()
    db_session.query(Vouch).delete()
    db_session.commit()


def test_resolve_vouch_rejects_non_admin_attacker_idor(client, db_session):
    voucher = Agent(address=VOUCHER_ADDR, karma=30)
    vouched = Agent(address=VOUCHED_ADDR, karma=0)
    attacker = Agent(address=ATTACKER_ADDR, karma=0)
    db_session.add_all([voucher, vouched, attacker])
    db_session.commit()

    vouch = Vouch(
        vouching_agent=VOUCHER_ADDR,
        vouched_agent=VOUCHED_ADDR,
        amount_at_stake=20_000_000,
        status="active",
    )
    db_session.add(vouch)
    db_session.commit()
    db_session.refresh(vouch)

    attacker_token = get_auth_token(client, ATTACKER_ADDR)
    voucher_token = get_auth_token(client, VOUCHER_ADDR)
    vouched_token = get_auth_token(client, VOUCHED_ADDR)

    with patch.object(type(settings), "ADMIN_ADDRESS", new_callable=PropertyMock, return_value=ADMIN_ADDR):
        for token in (attacker_token, voucher_token, vouched_token):
            for outcome in ("slashed", "resolved"):
                res = client.post(
                    f"/api/v1/cold-start/vouch/{vouch.id}/resolve?outcome={outcome}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert res.status_code == 403
                assert "Administrator access required" in res.json()["detail"]

    db_session.expire_all()
    assert vouch.status == "active"
    assert voucher.karma == 30
    assert vouched.karma == 0


def test_resolve_vouch_allows_admin_and_rejects_invalid_outcome(client, db_session):
    voucher = Agent(address=VOUCHER_ADDR, karma=30)
    vouched = Agent(address=VOUCHED_ADDR, karma=0)
    admin = Agent(address=ADMIN_ADDR, karma=100)
    db_session.add_all([voucher, vouched, admin])
    db_session.commit()

    vouch = Vouch(
        vouching_agent=VOUCHER_ADDR,
        vouched_agent=VOUCHED_ADDR,
        amount_at_stake=20_000_000,
        status="active",
    )
    db_session.add(vouch)
    db_session.commit()
    db_session.refresh(vouch)

    admin_token = get_auth_token(client, ADMIN_ADDR)
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch.object(type(settings), "ADMIN_ADDRESS", new_callable=PropertyMock, return_value=ADMIN_ADDR):
        bad_res = client.post(
            f"/api/v1/cold-start/vouch/{vouch.id}/resolve?outcome=invalid",
            headers=headers,
        )
        assert bad_res.status_code == 422

        db_session.expire_all()
        assert vouch.status == "active"

        ok_res = client.post(
            f"/api/v1/cold-start/vouch/{vouch.id}/resolve?outcome=resolved",
            headers=headers,
        )
        assert ok_res.status_code == 200
        data = ok_res.json()
        assert data["outcome"] == "resolved"
        assert data["vouching_karma_change"] == 5
        assert data["vouched_karma_change"] == 3

    db_session.expire_all()
    assert vouch.status == "resolved"
    assert voucher.karma == 35
    assert vouched.karma == 3


def test_release_collateral_rejects_self_release_by_depositor(client, db_session):
    depositor = Agent(address=DEPOSITOR_ADDR, karma=0, has_collateral=True)
    attacker = Agent(address=ATTACKER_ADDR, karma=0)
    db_session.add_all([depositor, attacker])
    db_session.commit()

    deposit = CollateralDeposit(
        agent_address=DEPOSITOR_ADDR,
        amount_microalgo=5_000_000,
        status="locked",
    )
    db_session.add(deposit)
    db_session.commit()
    db_session.refresh(deposit)

    depositor_token = get_auth_token(client, DEPOSITOR_ADDR)
    attacker_token = get_auth_token(client, ATTACKER_ADDR)

    with patch.object(type(settings), "ADMIN_ADDRESS", new_callable=PropertyMock, return_value=ADMIN_ADDR):
        for token in (depositor_token, attacker_token):
            res = client.post(
                f"/api/v1/cold-start/deposit/{deposit.id}/release?outcome=released",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 403
            assert "Administrator access required" in res.json()["detail"]

    db_session.expire_all()
    assert deposit.status == "locked"
    assert depositor.karma == 0
    assert depositor.has_collateral is True


def test_release_collateral_allows_admin_and_updates_depositor_not_admin(client, db_session):
    depositor = Agent(address=DEPOSITOR_ADDR, karma=0, has_collateral=True)
    admin = Agent(address=ADMIN_ADDR, karma=100)
    db_session.add_all([depositor, admin])
    db_session.commit()

    deposit = CollateralDeposit(
        agent_address=DEPOSITOR_ADDR,
        amount_microalgo=5_000_000,
        status="locked",
    )
    db_session.add(deposit)
    db_session.commit()
    db_session.refresh(deposit)

    admin_token = get_auth_token(client, ADMIN_ADDR)

    with patch.object(type(settings), "ADMIN_ADDRESS", new_callable=PropertyMock, return_value=ADMIN_ADDR):
        res = client.post(
            f"/api/v1/cold-start/deposit/{deposit.id}/release?outcome=released",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "released"
        assert data["agent_karma_change"] == 15
        assert data["agent_has_collateral"] is False

    db_session.expire_all()
    assert deposit.status == "released"
    assert depositor.karma == 15
    assert depositor.has_collateral is False
    assert admin.karma == 100


def test_release_collateral_admin_slash_clears_has_collateral_and_rejects_invalid_outcome(
    client, db_session
):
    depositor = Agent(address=DEPOSITOR_ADDR, karma=0, has_collateral=True)
    admin = Agent(address=ADMIN_ADDR, karma=100)
    db_session.add_all([depositor, admin])
    db_session.commit()

    deposit = CollateralDeposit(
        agent_address=DEPOSITOR_ADDR,
        amount_microalgo=5_000_000,
        status="locked",
    )
    db_session.add(deposit)
    db_session.commit()
    db_session.refresh(deposit)

    admin_token = get_auth_token(client, ADMIN_ADDR)
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch.object(type(settings), "ADMIN_ADDRESS", new_callable=PropertyMock, return_value=ADMIN_ADDR):
        bad_res = client.post(
            f"/api/v1/cold-start/deposit/{deposit.id}/release?outcome=bogus",
            headers=headers,
        )
        assert bad_res.status_code == 422

        db_session.expire_all()
        assert deposit.status == "locked"
        assert depositor.has_collateral is True
        assert depositor.karma == 0

        slash_res = client.post(
            f"/api/v1/cold-start/deposit/{deposit.id}/release?outcome=slashed",
            headers=headers,
        )
        assert slash_res.status_code == 200
        data = slash_res.json()
        assert data["status"] == "slashed"
        assert data["agent_karma_change"] == -5
        assert data["agent_has_collateral"] is False

    db_session.expire_all()
    assert deposit.status == "slashed"
    assert depositor.karma == -5
    assert depositor.has_collateral is False
