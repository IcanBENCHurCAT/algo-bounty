import jcs
import base64
import logging
from typing import Optional, Dict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

def canonicalize_json(payload: dict) -> bytes:
    """
    Format a JSON object/dict deterministically according to RFC 8785 (JCS).
    """
    return jcs.canonicalize(payload)

def verify_signature(public_key: str, payload_bytes: bytes, signature: str) -> bool:
    """
    Verify an ED25519 signature over a payload using a base64 or hex encoded public key.
    signature should be base64 encoded or hex encoded.
    """
    try:
        # Try base64 decode for the public key
        try:
            pub_key_bytes = base64.b64decode(public_key, validate=True)
            if len(pub_key_bytes) != 32:
                raise ValueError("Invalid ed25519 public key length from base64")
        except Exception:
            pub_key_bytes = bytes.fromhex(public_key)
            if len(pub_key_bytes) != 32:
                raise ValueError("Invalid ed25519 public key length from hex")

        # Decode the signature
        try:
            sig_bytes = base64.b64decode(signature, validate=True)
            if len(sig_bytes) != 64:
                raise ValueError("Invalid ed25519 signature length from base64")
        except Exception:
            sig_bytes = bytes.fromhex(signature)
            if len(sig_bytes) != 64:
                raise ValueError("Invalid ed25519 signature length from hex")

        key = Ed25519PublicKey.from_public_bytes(pub_key_bytes)
        key.verify(sig_bytes, payload_bytes)
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False
