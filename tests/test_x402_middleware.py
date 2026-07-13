import pytest
from fastapi.testclient import TestClient
from gateway.main import app
import time
import nacl.signing
from algosdk import encoding
from gateway.database import SessionLocal, Bounty, Agent
from gateway.auth import create_jwt_token
from unittest.mock import patch, MagicMock

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def setup_mock_db(db, address):
    # Setup agent
    agent = db.query(Agent).filter(Agent.address == address).first()
    if not agent:
        agent = Agent(address=address)
        db.add(agent)

    # Setup bounty
    bounty_id = "b_12345"
    bounty = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not bounty:
        bounty = Bounty(bounty_id=bounty_id, status="submitted", creator="test_creator", amount=200000, repo_url="test/test")
        db.add(bounty)
    else:
        bounty.status = "submitted"

    db.commit()
    return bounty_id

def test_x402_middleware_success(db_session):
    sk = nacl.signing.SigningKey.generate()
    address = encoding.encode_address(sk.verify_key.encode())

    bounty_id = setup_mock_db(db_session, address)

    timestamp = int(time.time())
    nonce = "test-nonce-success-1"
    amount = "200000"
    currency = "ALGO"
    scope = f"escrow-release:{bounty_id}"

    payload = f"{amount}{scope}{timestamp}{nonce}".encode("utf-8")
    signature = sk.sign(payload).signature.hex()

    token = create_jwt_token(address)

    # Mock Redis so it doesn't conflict or fail
    with patch("gateway.middleware.x402.redis_client.set") as mock_set:
        mock_set.return_value = True # mock nx=True success

        # In a real run, there might be no matching route for this path if we don't define one,
        # but the middleware runs BEFORE the router, and if it passes, it yields to the router (which might return 404, or actual response)
        # For our test, we just check if it DOES NOT return the middleware's custom errors.

        response = client.post(
            f"/api/v2/bounties/{bounty_id}/accept",
            headers={
                "Authorization": f"Bearer {token}",
                "x-402-amount": amount,
                "x-402-currency": currency,
                "x-402-scope": scope,
                "x-402-timestamp": str(timestamp),
                "x-402-nonce": nonce,
                "x-402-signature": signature
            }
        )

        # It should pass middleware and reach router, which will likely return 404 because the endpoint does not exist yet (as per instructions, just middleware was asked to be written).
        assert response.status_code == 404

def test_x402_middleware_expired_request(db_session):
    sk = nacl.signing.SigningKey.generate()
    address = encoding.encode_address(sk.verify_key.encode())
    bounty_id = setup_mock_db(db_session, address)

    timestamp = int(time.time()) - 400 # 400 seconds ago, beyond 300s window
    nonce = "test-nonce-expired"
    amount = "200000"
    currency = "ALGO"
    scope = f"escrow-release:{bounty_id}"

    payload = f"{amount}{scope}{timestamp}{nonce}".encode("utf-8")
    signature = sk.sign(payload).signature.hex()
    token = create_jwt_token(address)

    response = client.post(
        f"/api/v2/bounties/{bounty_id}/accept",
        headers={
            "Authorization": f"Bearer {token}",
            "x-402-amount": amount,
            "x-402-currency": currency,
            "x-402-scope": scope,
            "x-402-timestamp": str(timestamp),
            "x-402-nonce": nonce,
            "x-402-signature": signature
        }
    )

    assert response.status_code == 401
    assert "expired" in response.json()["error"].lower()

def test_x402_middleware_nonce_collision(db_session):
    sk = nacl.signing.SigningKey.generate()
    address = encoding.encode_address(sk.verify_key.encode())
    bounty_id = setup_mock_db(db_session, address)

    timestamp = int(time.time())
    nonce = "test-nonce-collision"
    amount = "200000"
    currency = "ALGO"
    scope = f"escrow-release:{bounty_id}"

    payload = f"{amount}{scope}{timestamp}{nonce}".encode("utf-8")
    signature = sk.sign(payload).signature.hex()
    token = create_jwt_token(address)

    with patch("gateway.middleware.x402.redis_client.set") as mock_set:
        mock_set.return_value = None # mock nx=True failure (key exists)

        response = client.post(
            f"/api/v2/bounties/{bounty_id}/accept",
            headers={
                "Authorization": f"Bearer {token}",
                "x-402-amount": amount,
                "x-402-currency": currency,
                "x-402-scope": scope,
                "x-402-timestamp": str(timestamp),
                "x-402-nonce": nonce,
                "x-402-signature": signature
            }
        )

        assert response.status_code == 401
        assert "replay attack" in response.json()["error"].lower()

def test_x402_middleware_invalid_signature(db_session):
    sk1 = nacl.signing.SigningKey.generate()
    sk2 = nacl.signing.SigningKey.generate()
    address1 = encoding.encode_address(sk1.verify_key.encode())

    bounty_id = setup_mock_db(db_session, address1)

    timestamp = int(time.time())
    nonce = "test-nonce-inv-sig"
    amount = "200000"
    currency = "ALGO"
    scope = f"escrow-release:{bounty_id}"

    payload = f"{amount}{scope}{timestamp}{nonce}".encode("utf-8")
    # Signed by wrong key!
    signature = sk2.sign(payload).signature.hex()

    token = create_jwt_token(address1)

    with patch("gateway.middleware.x402.redis_client.set") as mock_set:
        mock_set.return_value = True

        response = client.post(
            f"/api/v2/bounties/{bounty_id}/accept",
            headers={
                "Authorization": f"Bearer {token}",
                "x-402-amount": amount,
                "x-402-currency": currency,
                "x-402-scope": scope,
                "x-402-timestamp": str(timestamp),
                "x-402-nonce": nonce,
                "x-402-signature": signature
            }
        )

        assert response.status_code == 403
        assert "invalid signature" in response.json()["error"].lower()

def test_x402_middleware_unauthorized_scope(db_session):
    sk = nacl.signing.SigningKey.generate()
    address = encoding.encode_address(sk.verify_key.encode())
    bounty_id = setup_mock_db(db_session, address)

    timestamp = int(time.time())
    nonce = "test-nonce-scope"
    amount = "200000"
    currency = "ALGO"
    scope = "escrow-release:wrong_bounty_id"

    payload = f"{amount}{scope}{timestamp}{nonce}".encode("utf-8")
    signature = sk.sign(payload).signature.hex()
    token = create_jwt_token(address)

    with patch("gateway.middleware.x402.redis_client.set") as mock_set:
        mock_set.return_value = True

        response = client.post(
            f"/api/v2/bounties/{bounty_id}/accept",
            headers={
                "Authorization": f"Bearer {token}",
                "x-402-amount": amount,
                "x-402-currency": currency,
                "x-402-scope": scope,
                "x-402-timestamp": str(timestamp),
                "x-402-nonce": nonce,
                "x-402-signature": signature
            }
        )

        assert response.status_code == 403
        assert "unauthorized scope" in response.json()["error"].lower()

def test_x402_middleware_invalid_bounty_state(db_session):
    sk = nacl.signing.SigningKey.generate()
    address = encoding.encode_address(sk.verify_key.encode())
    bounty_id = setup_mock_db(db_session, address)

    # Change bounty state
    bounty = db_session.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    bounty.status = "open"
    db_session.commit()

    timestamp = int(time.time())
    nonce = "test-nonce-state"
    amount = "200000"
    currency = "ALGO"
    scope = f"escrow-release:{bounty_id}"

    payload = f"{amount}{scope}{timestamp}{nonce}".encode("utf-8")
    signature = sk.sign(payload).signature.hex()
    token = create_jwt_token(address)

    with patch("gateway.middleware.x402.redis_client.set") as mock_set:
        mock_set.return_value = True

        response = client.post(
            f"/api/v2/bounties/{bounty_id}/accept",
            headers={
                "Authorization": f"Bearer {token}",
                "x-402-amount": amount,
                "x-402-currency": currency,
                "x-402-scope": scope,
                "x-402-timestamp": str(timestamp),
                "x-402-nonce": nonce,
                "x-402-signature": signature
            }
        )

        assert response.status_code == 403
        assert "submitted state" in response.json()["error"].lower()
