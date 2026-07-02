from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import Agent
from ..auth import get_current_user
from ..dependencies import get_db

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

@router.get("/{address}")
def get_agent(address: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.address == address).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "address": agent.address,
        "karma": agent.karma,
        "completed_bounties": agent.completed_bounties,
        "disputes_lost": agent.disputes_lost
    }

@router.get("/me")
def get_my_profile(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return get_agent(current_user, db)
