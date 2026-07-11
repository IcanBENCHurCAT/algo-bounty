import pytest
import base64
import time
from unittest.mock import patch, MagicMock, AsyncMock
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from gateway.crypto import canonicalize_json, verify_signature, resolve_did_public_key, _did_cache, CACHE_TTL

@pytest.fixture(autouse=True)
def clear_cache():
    _did_cache.clear()
    yield
    _did_cache.clear()

def test_canonicalize_json():
    # RFC 8785 examples
    payload1 = {"b": 2, "a": 1}
    payload2 = {"a": 1, "b": 2}

    # Should sort keys and remove spaces
    assert canonicalize_json(payload1) == b'{"a":1,"b":2}'
    assert canonicalize_json(payload1) == canonicalize_json(payload2)

def test_verify_signature_valid_base64():
    # Generate keys
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    pub_bytes = public_key.public_bytes_raw()
    pub_b64 = base64.b64encode(pub_bytes).decode('utf-8')

    payload = b'{"a":1,"b":2}'
    sig_bytes = private_key.sign(payload)
    sig_b64 = base64.b64encode(sig_bytes).decode('utf-8')

    assert verify_signature(pub_b64, payload, sig_b64) is True

def test_verify_signature_valid_hex():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    pub_bytes = public_key.public_bytes_raw()
    pub_hex = pub_bytes.hex()

    payload = b'{"a":1,"b":2}'
    sig_bytes = private_key.sign(payload)
    sig_hex = sig_bytes.hex()

    assert verify_signature(pub_hex, payload, sig_hex) is True

def test_verify_signature_invalid():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_b64 = base64.b64encode(public_key.public_bytes_raw()).decode('utf-8')

    payload = b'{"a":1,"b":2}'
    sig_bytes = private_key.sign(payload)
    sig_b64 = base64.b64encode(sig_bytes).decode('utf-8')

    # Modify payload
    assert verify_signature(pub_b64, b'{"a":2,"b":1}', sig_b64) is False

    # Modify signature
    bad_sig_bytes = bytearray(sig_bytes)
    bad_sig_bytes[0] ^= 1
    bad_sig_b64 = base64.b64encode(bad_sig_bytes).decode('utf-8')
    assert verify_signature(pub_b64, payload, bad_sig_b64) is False

def test_verify_signature_invalid_format():
    # Not base64 or hex
    assert verify_signature("not a key", b"payload", "not a signature") is False

@pytest.mark.asyncio
async def test_resolve_did_unsupported_method():
    assert await resolve_did_public_key("did:unsupported:123") is None

@pytest.mark.asyncio
@patch('gateway.crypto.httpx.AsyncClient')
async def test_resolve_did_success_base64(mock_client_class):
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "verificationMethod": [{
            "id": "did:web:agent.example.com#key-1",
            "type": "Ed25519VerificationKey2018",
            "controller": "did:web:agent.example.com",
            "publicKeyBase64": "test_pub_key_base64"
        }]
    }
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await resolve_did_public_key("did:web:agent.example.com")

    assert result == "test_pub_key_base64"
    assert "did:web:agent.example.com" in _did_cache
    mock_client.get.assert_called_once_with("https://agent.example.com/.well-known/did.json")

@pytest.mark.asyncio
@patch('gateway.crypto.httpx.AsyncClient')
async def test_resolve_did_success_hex(mock_client_class):
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "verificationMethod": [{
            "publicKeyHex": "414243"  # "ABC" in hex
        }]
    }
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await resolve_did_public_key("did:web:agent.example.com")

    assert result == base64.b64encode(b"ABC").decode('utf-8')

@pytest.mark.asyncio
@patch('gateway.crypto.httpx.AsyncClient')
async def test_resolve_did_success_multibase_ed25519(mock_client_class):
    mock_client = AsyncMock()
    mock_response = MagicMock()
    import base58
    # Ed25519 32-byte key
    raw_key = b"x" * 32
    # multicodec ed25519-pub (0xed01) + raw_key
    multicodec_key = b'\xed\x01' + raw_key
    # Multibase base58btc ('z' prefix)
    mb = "z" + base58.b58encode(multicodec_key).decode('utf-8')

    mock_response.json.return_value = {
        "verificationMethod": [{
            "publicKeyMultibase": mb
        }]
    }
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await resolve_did_public_key("did:web:agent.example.com")

    assert result == base64.b64encode(raw_key).decode('utf-8')

@pytest.mark.asyncio
@patch('gateway.crypto.httpx.AsyncClient')
async def test_resolve_did_success_multibase_raw(mock_client_class):
    mock_client = AsyncMock()
    mock_response = MagicMock()
    import base58
    # raw key without multicodec prefix (non-standard but sometimes used)
    raw_key = b"x" * 32
    mb = "z" + base58.b58encode(raw_key).decode('utf-8')

    mock_response.json.return_value = {
        "verificationMethod": [{
            "publicKeyMultibase": mb
        }]
    }
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await resolve_did_public_key("did:web:agent.example.com")

    assert result == base64.b64encode(raw_key).decode('utf-8')

@pytest.mark.asyncio
async def test_resolve_did_cache_hit():
    _did_cache["did:web:cached.example.com"] = ("cached_pub_key", time.time() + CACHE_TTL)

    result = await resolve_did_public_key("did:web:cached.example.com")

    assert result == "cached_pub_key"

@pytest.mark.asyncio
@patch('gateway.crypto.httpx.AsyncClient')
async def test_resolve_did_cache_expired(mock_client_class):
    _did_cache["did:web:expired.example.com"] = ("expired_pub_key", time.time() - 10)

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "verificationMethod": [{
            "publicKeyBase64": "new_pub_key"
        }]
    }
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await resolve_did_public_key("did:web:expired.example.com")

    assert result == "new_pub_key"
    assert "did:web:expired.example.com" in _did_cache

@pytest.mark.asyncio
@patch('gateway.crypto.httpx.AsyncClient')
async def test_resolve_did_http_error(mock_client_class):
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("HTTP Error")
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await resolve_did_public_key("did:web:error.example.com")

    assert result is None
    assert "did:web:error.example.com" not in _did_cache
