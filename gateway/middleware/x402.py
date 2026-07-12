import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import nacl.signing
import nacl.encoding
from gateway.database import SessionLocal, Agent, Bounty
from typing import Optional

try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
except ImportError:
    class DummyRedis:
        def set(self, *args, **kwargs):
            return True
    redis_client = DummyRedis()

class X402Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if request.method == "OPTIONS":
            return await call_next(request)

        # Only intercept /api/v2/bounties/{id}/accept or related matching endpoints
        if not ("/api/v2/bounties/" in path and path.endswith("/accept")):
            return await call_next(request)

        # Ensure headers are present
        amount = request.headers.get("x-402-amount")
        currency = request.headers.get("x-402-currency")
        scope = request.headers.get("x-402-scope")
        timestamp_str = request.headers.get("x-402-timestamp")
        nonce = request.headers.get("x-402-nonce")
        signature_hex = request.headers.get("x-402-signature")

        if not all([amount, currency, scope, timestamp_str, nonce, signature_hex]):
            return Response(
                content='{"error": "Missing one or more required x402 headers"}',
                status_code=400,
                media_type="application/json",
            )

        try:
            timestamp = int(timestamp_str)
        except ValueError:
            return Response(
                content='{"error": "Invalid x-402-timestamp"}',
                status_code=400,
                media_type="application/json",
            )

        current_time = int(time.time())

        # 1. Expiration check (300s window)
        if abs(current_time - timestamp) > 300:
            return Response(
                content='{"error": "Request expired or timestamp too far in future"}',
                status_code=401,
                media_type="application/json",
            )

        # 2. Redis-based double-spend/replay check
        if redis_client is not None:
            try:
                if redis_client.set(f"nonce:{nonce}", "1", ex=300, nx=True) is None:
                    return Response(
                        content='{"error": "Replay attack detected (nonce reused)"}',
                        status_code=401,
                        media_type="application/json",
                    )
            except Exception:
                 pass # allow pass if redis is not running or connection fails

        # Extract bounty ID from path to map scope and check bounty state
        path_parts = path.strip("/").split("/")
        bounty_id = None
        for i, p in enumerate(path_parts):
            if p == "bounties" and i + 1 < len(path_parts):
                bounty_id = path_parts[i + 1]
                break

        if not bounty_id:
             return Response(
                content='{"error": "Invalid bounty path"}',
                status_code=400,
                media_type="application/json",
            )

        expected_scope = f"escrow-release:{bounty_id}"
        if scope != expected_scope:
            return Response(
                content='{"error": "Unauthorized scope"}',
                status_code=403,
                media_type="application/json",
            )

        # Check bounty state
        db = SessionLocal()
        bounty = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()

        if not bounty:
            db.close()
            return Response(
                content='{"error": "Bounty not found"}',
                status_code=404,
                media_type="application/json",
            )

        if bounty.status != "submitted":
            db.close()
            return Response(
                content='{"error": "Bounty must be in submitted state"}',
                status_code=403,
                media_type="application/json",
            )

        # 3. Cryptographic verify over canonical JCS structure
        # JCS canonicalization logic expects keys sorted, compact spacing, escaped chars.
        # But per the AP2 docs, the specific payload here is simple string concatenation:
        sig_payload = f"{amount}{scope}{timestamp_str}{nonce}".encode("utf-8")

        # Get user's agent from database to get pub key
        # Extract JWT to get address, assuming Authorization header is present
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            db.close()
            return Response(
                content='{"error": "Missing or invalid Authorization header"}',
                status_code=401,
                media_type="application/json",
            )

        token = auth_header.replace("Bearer ", "")

        from gateway.auth import verify_jwt_token
        try:
             address = verify_jwt_token(token)
        except Exception as e:
             db.close()
             return Response(
                 content='{"error": "Invalid session token"}',
                 status_code=401,
                 media_type="application/json",
             )

        agent = db.query(Agent).filter(Agent.address == address).first()
        db.close()

        if not agent:
             return Response(
                 content='{"error": "Agent not found"}',
                 status_code=404,
                 media_type="application/json",
             )

        # In AP2 docs, "public_key" is on Agent Registry Table. Let's decode address.
        # The agent's address in Algorand IS the public key when decoded.
        from algosdk import encoding
        try:
             public_key_bytes = encoding.decode_address(agent.address)
             verify_key = nacl.signing.VerifyKey(public_key_bytes)
             verify_key.verify(sig_payload, bytes.fromhex(signature_hex))
        except nacl.exceptions.BadSignatureError:
             return Response(
                 content='{"error": "Invalid signature"}',
                 status_code=403,
                 media_type="application/json",
             )
        except Exception as e:
             return Response(
                 content=f'{{"error": "Signature verification failed: {str(e)}"}}',
                 status_code=400,
                 media_type="application/json",
             )

        return await call_next(request)
