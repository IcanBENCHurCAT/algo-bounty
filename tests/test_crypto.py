import pytest
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from gateway.crypto import canonicalize_json, verify_signature

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
