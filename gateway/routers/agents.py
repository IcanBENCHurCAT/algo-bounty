from ..schemas import AgentProfileResponse, AgentLinkGitHub, StewardRegisterRequest, StewardRegisterResponse
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
        "disputes_lost": agent.disputes_lost,
        "steward_name": agent.steward_name,
        "steward_email": agent.steward_email,
        "steward_verified": agent.steward_verified,
        "steward_stablecoin_address": agent.steward_stablecoin_address,
        "steward_of": agent.steward_of,
        "steward_of_steward_address": agent.steward_of_steward_address,
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
        "disputes_lost": agent.disputes_lost,
        "steward_name": agent.steward_name,
        "steward_email": agent.steward_email,
        "steward_verified": agent.steward_verified,
        "steward_stablecoin_address": agent.steward_stablecoin_address,
        "steward_of": agent.steward_of,
        "steward_of_steward_address": agent.steward_of_steward_address,
    }

# ─── Stewardship endpoints (Legal #165) ────────────────────────────────

@router.put(
    "/me/steward",
    response_model=StewardRegisterResponse,
    summary="Register a human steward for this agent",
    description="Link a human steward (name, email, optional stablecoin address) to the authenticated agent's profile. "
    "The steward assumes full legal, tax, and financial responsibility per Constitution §5.8. "
    "steward_verified is False on registration; it is set to True by the platform after manual or KYA verification."
)
def register_steward(body: StewardRegisterRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile missing")

    agent.steward_name = body.steward_name
    agent.steward_email = body.steward_email
    agent.steward_stablecoin_address = body.steward_stablecoin_address
    # Pre-mainnet: auto-verify since there's no KYA integration yet
    agent.steward_verified = True
    db.commit()
    db.refresh(agent)

    return {
        "status": "registered",
        "steward_name": agent.steward_name,
        "steward_email": agent.steward_email,
        "steward_verified": agent.steward_verified,
    }

@router.get(
    "/steward/{steward_address}",
    response_model=list[AgentProfileResponse],
    summary="List all agents for a steward address",
    description="Return all agent profiles that reference the given steward wallet address via steward_of_steward_address. "
    "This links multiple agent addresses to a single human steward per Constitution §5.8."
)
def list_agents_for_steward(steward_address: str, db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(
        Agent.steward_of_steward_address == steward_address
    ).all()
    result = []
    for a in agents:
        result.append({
            "address": a.address,
            "github_username": a.github_username,
            "karma": a.karma,
            "completed_bounties": a.completed_bounties,
            "disputes_lost": a.disputes_lost,
            "steward_name": a.steward_name,
            "steward_email": a.steward_email,
            "steward_verified": a.steward_verified,
            "steward_stablecoin_address": a.steward_stablecoin_address,
            "steward_of": a.steward_of,
            "steward_of_steward_address": a.steward_of_steward_address,
        })
    return result
