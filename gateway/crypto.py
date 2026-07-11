import jcs
import base64
import time
import httpx
import logging
from typing import Optional, Dict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

# Basic in-memory cache for DID resolution
# Map of DID -> (public_key_base64, expires_at)
_did_cache: Dict[str, tuple[str, float]] = {}
CACHE_TTL = 86400  # 24 hours in seconds

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

async def resolve_did_public_key(did: str) -> Optional[str]:
    """
    Resolve a did:web public key by fetching its DID document.
    Caches the result in memory for 24 hours.
    Returns the public key as a base64 string.
    """
    if not did.startswith("did:web:"):
        logger.error(f"Unsupported DID method in {did}")
        return None

    current_time = time.time()

    # Check cache
    if did in _did_cache:
        pubkey, expires_at = _did_cache[did]
        if current_time < expires_at:
            return pubkey
        else:
            del _did_cache[did]

    # Resolve did:web
    domain = did[8:]
    domain_path = domain.replace(":", "/")
    url = f"https://{domain_path}/.well-known/did.json"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            did_doc = response.json()

            # Extract verification method
            verification_methods = did_doc.get("verificationMethod", [])
            for vm in verification_methods:
                if "publicKeyBase64" in vm:
                    pubkey = vm["publicKeyBase64"]
                    _did_cache[did] = (pubkey, current_time + CACHE_TTL)
                    return pubkey
                elif "publicKeyHex" in vm:
                    pubkey = base64.b64encode(bytes.fromhex(vm["publicKeyHex"])).decode('utf-8')
                    _did_cache[did] = (pubkey, current_time + CACHE_TTL)
                    return pubkey
                elif "publicKeyJwk" in vm and vm["publicKeyJwk"].get("crv") == "Ed25519":
                    x_b64url = vm["publicKeyJwk"].get("x", "")
                    x_b64 = x_b64url.replace("-", "+").replace("_", "/")
                    x_b64 += "=" * ((4 - len(x_b64) % 4) % 4)
                    _did_cache[did] = (x_b64, current_time + CACHE_TTL)
                    return x_b64
                elif "publicKeyMultibase" in vm:
                    mb = vm["publicKeyMultibase"]
                    # Usually Multibase ed25519 keys start with 'z' for base58btc
                    if mb.startswith("z"):
                        import base58
                        # The prefix includes multicodec prefix for ed25519-pub (0xed01)
                        decoded = base58.b58decode(mb[1:])
                        # Stripping the 2-byte multicodec prefix if present
                        if decoded.startswith(b'\xed\x01'):
                            raw_key = decoded[2:]
                        else:
                            raw_key = decoded
                        pubkey = base64.b64encode(raw_key).decode('utf-8')
                        _did_cache[did] = (pubkey, current_time + CACHE_TTL)
                        return pubkey

            logger.error(f"No suitable public key found in DID doc for {did}")
            return None
    except Exception as e:
        logger.error(f"Failed to resolve DID {did}: {e}")
        return None
