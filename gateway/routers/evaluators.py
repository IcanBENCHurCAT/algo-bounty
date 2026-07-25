from ..schemas import EvaluatorRegistrationResponse, EvaluatorVoteResponse, EvaluatorResponse, EvaluatorListResponse, EvaluatorMeResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

from ..database import Agent, Evaluator, DisputeEvaluator, Bounty
from ..dependencies import get_db
from ..auth import get_current_user
from ..algod_client import get_algod_client, send_signed_transaction
from ..config import settings
from ..broker import broker

router = APIRouter(prefix="/api/v1/evaluators", tags=["evaluators"])

class VoteRequest(BaseModel):
    vote: str  # "worker", "payer", or "split"
    signed_txn: Optional[str] = None

@router.get("", response_model=EvaluatorListResponse, summary="List evaluators")
def list_evaluators(db: Session = Depends(get_db)):
    evaluators = db.query(Evaluator).filter(Evaluator.status == "active").all()
    results = []
    for ev in evaluators:
        agent = db.query(Agent).filter(Agent.address == ev.address).first()
        results.append(EvaluatorResponse(
            address=ev.address,
            status=ev.status,
            karma=agent.karma if agent else 0,
            disputes_lost=agent.disputes_lost if agent else 0
        ))
    return {"evaluators": results, "total": len(results)}

@router.get("/me", response_model=EvaluatorMeResponse, summary="Get my evaluator status")
def get_my_evaluator_status(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    karma = agent.karma if agent else 0
    evaluator = db.query(Evaluator).filter(Evaluator.address == current_user).first()
    status = evaluator.status if evaluator else "inactive"
    return {
        "address": current_user,
        "status": status,
        "karma": karma,
        "can_register": karma >= 50
    }

@router.post("/register", response_model=EvaluatorResponse, summary="Register as evaluator", description="Register the authenticated high-karma agent as an evaluator candidate.")
def register_evaluator(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    if agent.karma < 50:
        raise HTTPException(status_code=403, detail="Insufficient karma to register as evaluator. Requires at least 50.")

    evaluator = db.query(Evaluator).filter(Evaluator.address == current_user).first()
    if evaluator:
        if evaluator.status == "active":
            return {"address": current_user, "status": "active", "karma": agent.karma, "disputes_lost": agent.disputes_lost}
        else:
            evaluator.status = "active"
            evaluator.registered_at = datetime.now(timezone.utc)
    else:
        evaluator = Evaluator(
            address=current_user,
            status="active",
            registered_at=datetime.now(timezone.utc)
        )
        db.add(evaluator)
    
    db.commit()
    broker.publish("evaluator.registered", {"address": current_user})
    return {"address": current_user, "status": "active", "karma": agent.karma, "disputes_lost": agent.disputes_lost}

@router.post("/deregister", response_model=EvaluatorResponse, summary="Deregister as evaluator", description="Deregister the authenticated agent from the evaluator candidate pool.")
def deregister_evaluator(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    evaluator = db.query(Evaluator).filter(Evaluator.address == current_user).first()
    if not evaluator or evaluator.status == "inactive":
        raise HTTPException(status_code=400, detail="Not registered as an active evaluator")

    evaluator.status = "inactive"
    db.commit()
    broker.publish("evaluator.deregistered", {"address": current_user})
    
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    return {"address": current_user, "status": "inactive", "karma": agent.karma if agent else 0, "disputes_lost": agent.disputes_lost if agent else 0}

@router.post("/bounties/{bounty_id}/vote", response_model=EvaluatorVoteResponse, summary="Cast vote on dispute", description="Allows an assigned evaluator to cast their vote on a disputed bounty.")
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

    assignment = db.query(DisputeEvaluator).filter(
        DisputeEvaluator.bounty_id == bounty_id,
        DisputeEvaluator.evaluator_address == current_user
    ).first()

    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned as an evaluator for this dispute")
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

    broker.publish("evaluator.voted", {
        "bounty_id": bounty_id,
        "evaluator": current_user,
        "vote": vote_val,
        "tx_id": tx_id
    })

    return {"status": "voted", "bounty_id": bounty_id, "vote": vote_val, "tx_id": tx_id}
