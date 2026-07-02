from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import Agent
from ..auth import generate_challenge, verify_signature, create_jwt_token
from ..dependencies import get_db
from ..schemas import AuthRequest, AuthVerify

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/request")
def auth_request(body: AuthRequest):
    challenge = generate_challenge(body.address)
    return {
        "challenge": challenge,
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"
    }

@router.post("/verify")
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
        "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
        "karma": agent.karma
    }
