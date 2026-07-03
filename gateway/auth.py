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

def verify_signature(address: str, signature: str, challenge: str) -> bool:
    """Verify that the signature matches the Algorand address and challenge."""
    try:
        # standard SDK verify_bytes expects (bytes_message, signature_b64, address)
        # Note: In PyAlgoSDK, verify_bytes takes bytes for both message and signature.
        message_bytes = challenge.encode('utf-8')
        # Some clients return signature as base64 or bytes. If it's a string, we decode it
        # but algosdk.util.verify_bytes requires signature in base64 string or bytes?
        # Let's write a robust verification that checks verify_bytes.
        return util.verify_bytes(message_bytes, signature, address)
    except Exception as e:
        print(f"Signature verification failed: {e}")
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
