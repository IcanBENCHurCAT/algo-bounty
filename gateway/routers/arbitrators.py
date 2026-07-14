from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

from ..database import Agent, Arbitrator, DisputeArbitrator, Bounty
from ..dependencies import get_db
from ..auth import get_current_user
from ..algod_client import get_algod_client, send_signed_transaction
from ..config import settings
from ..broker import broker

router = APIRouter(prefix="/api/v1/arbitrators", tags=["arbitrators"])

class VoteRequest(BaseModel):
    vote: str  # "worker", "payer", or "split"
    signed_txn: Optional[str] = None

@router.post("/register", summary="Register as arbitrator", description="Register the authenticated high-karma agent as an arbitrator candidate.")
def register_arbitrator(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    if agent.karma < 50:
        raise HTTPException(status_code=403, detail="Insufficient karma to register as arbitrator. Requires at least 50.")

    arbitrator = db.query(Arbitrator).filter(Arbitrator.address == current_user).first()
    if arbitrator:
        if arbitrator.status == "active":
            return {"status": "already_registered", "address": current_user}
        else:
            arbitrator.status = "active"
            arbitrator.registered_at = datetime.now(timezone.utc)
    else:
        arbitrator = Arbitrator(
            address=current_user,
            status="active",
            registered_at=datetime.now(timezone.utc)
        )
        db.add(arbitrator)
    
    db.commit()
    broker.publish("arbitrator.registered", {"address": current_user})
    return {"status": "registered", "address": current_user}

@router.post("/deregister", summary="Deregister as arbitrator", description="Deregister the authenticated agent from the arbitrator candidate pool.")
def deregister_arbitrator(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    arbitrator = db.query(Arbitrator).filter(Arbitrator.address == current_user).first()
    if not arbitrator or arbitrator.status == "inactive":
        raise HTTPException(status_code=400, detail="Not registered as an active arbitrator")

    arbitrator.status = "inactive"
    db.commit()
    broker.publish("arbitrator.deregistered", {"address": current_user})
    return {"status": "deregistered", "address": current_user}

@router.post("/bounties/{bounty_id}/vote", summary="Cast vote on dispute", description="Allows an assigned arbitrator to cast their vote on a disputed bounty.")
def vote_dispute(
    bounty_id: str,
    body: VoteRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    bounty = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if bounty.status != "disputed":
        raise HTTPException(status_code=400, detail="Bounty is not in disputed state")

    vote_val = body.vote.lower()
    if vote_val not in ["worker", "payer", "split"]:
        raise HTTPException(status_code=400, detail="Invalid vote option. Must be worker, payer, or split")

    assignment = db.query(DisputeArbitrator).filter(
        DisputeArbitrator.bounty_id == bounty_id,
        DisputeArbitrator.arbitrator_address == current_user
    ).first()

    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned as an arbitrator for this dispute")
    if assignment.vote is not None:
        raise HTTPException(status_code=400, detail="You have already cast your vote for this dispute")

    if settings.ALGORAND_NETWORK != "sandbox" and not body.signed_txn:
        raise HTTPException(status_code=400, detail="signed_txn is required")

    tx_id = None
    if body.signed_txn:
        try:
            tx_id = send_signed_transaction(body.signed_txn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"On-chain transaction failed: {e}")

    assignment.vote = vote_val
    assignment.voted_at = datetime.now(timezone.utc)
    db.commit()

    broker.publish("arbitrator.voted", {
        "bounty_id": bounty_id,
        "arbitrator": current_user,
        "vote": vote_val,
        "tx_id": tx_id
    })

    return {"status": "voted", "bounty_id": bounty_id, "vote": vote_val, "tx_id": tx_id}
