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
    addr = "addr"
    ch = generate_challenge(addr)
    assert addr in ch

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
    import sys
    from importlib import reload
    with patch.dict("os.environ", {"SECRET_KEY": ""}):
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

