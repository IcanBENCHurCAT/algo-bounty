import pytest
from unittest.mock import patch
from fastapi import HTTPException
from gateway.auth import (
    generate_challenge,
    verify_signature,
    create_jwt_token,
    verify_jwt_token,
    get_current_user
)

def test_generate_challenge():
    addr = "ALGORAND_ADDRESS_12345"
    ch = generate_challenge(addr)
    assert ch.startswith(f"AlgoBounty auth: {addr} at ")
    timestamp_str = ch.split(" at ")[-1]
    assert timestamp_str.isdigit()

def test_generate_challenge_timestamp_mocking():
    mock_timestamp = 1700000000
    addr = "TEST_ADDRESS_67890"
    with patch("time.time", return_value=mock_timestamp):
        ch = generate_challenge(addr)
        assert ch == f"AlgoBounty auth: {addr} at 1700000000"

@pytest.mark.parametrize("input_address", [
    "",
    "   ",
    "addr_with_spaces ",
    "special!@#$%^&*()_+-=",
    "unicode_地址_ test"
])
def test_generate_challenge_edge_cases(input_address):
    ch = generate_challenge(input_address)
    assert f"AlgoBounty auth: {input_address} at " in ch
    timestamp_str = ch.rsplit(" at ", 1)[-1]
    assert timestamp_str.isdigit()

def test_verify_signature_exceptions():
    with patch("gateway.auth.util.verify_bytes", side_effect=Exception("verify error")):
        assert verify_signature("addr", "sig", "ch") is False

def test_verify_jwt_token_expired():
    import jwt
    import time
    from gateway.auth import SECRET_KEY, ALGORITHM
    
    payload = {"sub": "addr", "iat": int(time.time()), "exp": int(time.time()) - 10}
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as excinfo:
        verify_jwt_token(expired_token)
    assert excinfo.value.status_code == 401
    assert "Session expired" in excinfo.value.detail

def test_verify_jwt_token_invalid():
    with pytest.raises(HTTPException) as excinfo:
        verify_jwt_token("invalid_token_garbage")
    assert excinfo.value.status_code == 401
    assert "Invalid token" in excinfo.value.detail

def test_get_current_user_invalid_session():
    from fastapi.security import HTTPAuthorizationCredentials
    import jwt
    import time
    from gateway.auth import SECRET_KEY, ALGORITHM
    
    # Token without 'sub' claim
    payload = {"iat": int(time.time()), "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(creds)
    assert excinfo.value.status_code == 401
    assert "Invalid session" in excinfo.value.detail

def test_secret_key_missing_error():
    import os
    import sys
    from importlib import reload
    with patch.dict(os.environ, {"SECRET_KEY": ""}):
        with pytest.raises(RuntimeError) as excinfo:
            import gateway.auth
            reload(gateway.auth)
        assert "SECRET_KEY secret is not set" in str(excinfo.value)
    
    # Restore correct SECRET_KEY in gateway.auth
    import gateway.auth
    reload(gateway.auth)

def test_auth_verify_router_endpoints(client, db_session):
    # 1. Invalid signature
    res = client.post("/api/v1/auth/verify", json={
        "address": "ADDR_INVALID",
        "signature": "sig",
        "challenge": "ch"
    })
    assert res.status_code == 401
    assert "Invalid wallet signature" in res.json()["detail"]
    
    # 2. Valid signature for a new agent (implicit registration)
    with patch("gateway.routers.auth.verify_signature", return_value=True):
        res = client.post("/api/v1/auth/verify", json={
            "address": "NEW_ADDR_IMPLICIT",
            "signature": "sig",
            "challenge": "ch"
        })
        assert res.status_code == 200
        assert res.json()["address"] == "NEW_ADDR_IMPLICIT"
        assert res.json()["karma"] == 25

def test_verify_signature_transaction():
    from algosdk import account, transaction, encoding
    import base64
    from gateway.auth import verify_signature

    private_key, address = account.generate_account()
    challenge = "test_challenge_123"
    sp = transaction.SuggestedParams(1000, 10, 100, "", flat_fee=True)
    txn = transaction.PaymentTxn(address, sp, address, 0, note=f"auth:{challenge}".encode('utf-8'))
    signed_txn = txn.sign(private_key)

    encoded_stxn = encoding.msgpack_encode(signed_txn)

    assert verify_signature(address, encoded_stxn, challenge) is True

