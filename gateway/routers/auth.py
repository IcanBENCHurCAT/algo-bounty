from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import Agent
from ..auth import generate_challenge, verify_signature, create_jwt_token
from ..dependencies import get_db
from ..schemas import AuthRequest, AuthVerify

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/request", summary="Request auth challenge", description="Generate a unique cryptographic challenge for a wallet address. The user must sign this challenge with their private key to authenticate.")
def auth_request(body: AuthRequest):
    challenge = generate_challenge(body.address)
    return {
        "challenge": challenge,
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    }

@router.post("/verify", summary="Verify signature and login", description="Verify the wallet signature against the challenge. If valid, returns a JWT session token. Creates a new agent profile with 25 karma if one doesn't exist.")
def auth_verify(body: AuthVerify, db: Session = Depends(get_db)):
    # Verify the signature
    is_valid = verify_signature(body.address, body.signature, body.challenge)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid wallet signature")

    # Get or create agent
    agent = db.query(Agent).filter(Agent.address == body.address).first()
    if not agent:
        agent = Agent(address=body.address, karma=25)
        db.add(agent)
        db.commit()
        db.refresh(agent)

    # Generate JWT
    token = create_jwt_token(body.address)
    return {
        "jwt": token,
        "address": body.address,
        "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "karma": agent.karma
    }
