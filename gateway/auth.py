import time
import jwt
from typing import Optional
from algosdk import util
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings

SECRET_KEY = settings.SECRET_KEY
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY secret is not set. For security, the gateway cannot start without a JWT secret.")

ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 86400  # 24 hours

security = HTTPBearer()

def generate_challenge(address: str) -> str:
    """Generate a cryptographic auth challenge string containing current timestamp."""
    timestamp = int(time.time())
    return f"AlgoBounty auth: {address} at {timestamp}"

import base64
from algosdk import util, encoding, transaction

def verify_signature(address: str, signature: str, challenge: str) -> bool:
    """Verify that the signature matches the Algorand address and challenge.
    Supports both raw bytes signatures (ARC-60 / Lute) and transaction-based signatures.
    """
    try:
        # First, try to decode as a standard data signature
        message_bytes = challenge.encode('utf-8')
        try:
            if util.verify_bytes(message_bytes, signature, address):
                return True
        except Exception:
            pass

        # If that fails, try to decode as an unsendable transaction
        try:
            stxn = encoding.msgpack_decode(signature)
            if not isinstance(stxn, transaction.SignedTransaction):
                return False

            txn = stxn.transaction
            # Verify the note field matches the challenge
            expected_note = f"auth:{challenge}".encode('utf-8')
            if txn.note != expected_note:
                return False

            # Verify sender matches
            if txn.sender != address:
                return False

            # Verify it's a 0 ALGO payment to self
            if not isinstance(txn, transaction.PaymentTxn):
                return False
            if txn.receiver != address or txn.amt != 0:
                return False

            # Verify the signature itself
            return verify_txn_signature(stxn, address)
        except Exception as e:
            print(f"Txn verification failed: {e}")
            pass

    except Exception as e:
        print(f"Signature verification failed: {e}")

    return False

def verify_txn_signature(stxn: transaction.SignedTransaction, address: str) -> bool:
    try:
        public_key = encoding.decode_address(address)
        # If it has a multisig or logicsig, reject for this simple auth
        if getattr(stxn, "msig", None) or getattr(stxn, "lsig", None):
            return False

        import nacl.signing
        verify_key = nacl.signing.VerifyKey(public_key)

        # The correct way to get the message to verify for a transaction in py-algorand-sdk
        # is prefixing 'TX' to the msgpack encoded raw transaction
        # Actually msgpack_encode returns base64 string, so we need to decode it first
        import base64
        raw_txn_bytes = base64.b64decode(encoding.msgpack_encode(stxn.transaction))
        signable_bytes = b"TX" + raw_txn_bytes

        verify_key.verify(signable_bytes, base64.b64decode(stxn.signature))
        return True
    except Exception as e:
        print(f"verify_txn_signature error: {e}")
        return False

def create_jwt_token(address: str) -> str:
    """Generate a JWT session token for the authenticated wallet address."""
    payload = {
        "sub": address,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt_token(token: str) -> Optional[str]:
    """Verify the JWT token and return the wallet address."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Dependency injection to get the current authenticated user address."""
    token = credentials.credentials
    address = verify_jwt_token(token)
    if not address:
        raise HTTPException(status_code=401, detail="Invalid session")
    return address
