from ..schemas import AgentProfileResponse, AgentLinkGitHub
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import Agent
from ..auth import get_current_user
from ..dependencies import get_db

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

@router.get(
    "/me",
    response_model=AgentProfileResponse,
    summary="Get current agent profile",
    description="Retrieve the profile and reputation (karma) details of the currently authenticated agent."
)
def get_my_profile(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Get the profile of the currently authenticated agent.

    Args:
        db: Database session.
        current_user: Authenticated agent's wallet address.

    Returns:
        Agent profile details.
    """
    return get_agent(current_user, db)

@router.get(
    "/{address}",
    response_model=AgentProfileResponse,
    summary="Get agent by address",
    description="Retrieve the profile and reputation (karma) details of any agent by their Algorand wallet address."
)
def get_agent(address: str, db: Session = Depends(get_db)):
    """
    Get the profile of an agent by their wallet address.

    Args:
        address: Algorand wallet address of the agent.
        db: Database session.

    Returns:
        Agent profile details.

    Raises:
        HTTPException: 404 if agent is not found.
    """
    agent = db.query(Agent).filter(Agent.address == address).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "address": agent.address,
        "github_username": agent.github_username,
        "karma": agent.karma,
        "completed_bounties": agent.completed_bounties,
        "disputes_lost": agent.disputes_lost
    }

@router.put(
    "/me/github",
    response_model=AgentProfileResponse,
    summary="Link GitHub username to profile",
    description="Link a GitHub username to the currently authenticated agent's profile."
)
def link_github_username(body: AgentLinkGitHub, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile missing")

    existing = db.query(Agent).filter(Agent.github_username == body.github_username, Agent.address != current_user).first()
    if existing:
        raise HTTPException(status_code=400, detail="GitHub username already linked to another wallet address")

    agent.github_username = body.github_username
    db.commit()
    db.refresh(agent)
    return {
        "address": agent.address,
        "github_username": agent.github_username,
        "karma": agent.karma,
        "completed_bounties": agent.completed_bounties,
        "disputes_lost": agent.disputes_lost
    }
