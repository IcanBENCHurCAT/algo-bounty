from datetime import datetime, timezone
from ..schemas import (AgentProfileResponse, AgentLinkGitHub,
    StewardRegisterRequest, StewardRegisterResponse,
    TaxUpdateRequest, TaxUpdateResponse, PayoutSummaryResponse,
    WithholdingConfigResponse)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import Agent
from ..auth import get_current_user
from ..dependencies import get_db

# Tax withholding rates by jurisdiction (simplified schedule)
TAX_WITHHOLDING_SCHEDULE = {
    "US": {"rate": 0.24, "threshold_usd": 600.0, "form": "W-9",
           "desc": "24% federal backup withholding applies to payouts >$600/yr for US persons"},
    "DE": {"rate": 0.0, "threshold_usd": 600.0, "form": "W-8BEN",
           "desc": "No US withholding under US-Germany tax treaty; self-report in home jurisdiction"},
    "GB": {"rate": 0.0, "threshold_usd": 600.0, "form": "W-8BEN",
           "desc": "No US withholding under US-UK tax treaty"},
    "IN": {"rate": 0.25, "threshold_usd": 600.0, "form": "W-8BEN",
           "desc": "25% treaty rate applies for Indian residents with valid W-8BEN"},
    "CA": {"rate": 0.0, "threshold_usd": 600.0, "form": "W-8BEN",
           "desc": "No US withholding under US-Canada tax treaty"},
    "AU": {"rate": 0.0, "threshold_usd": 600.0, "form": "W-8BEN",
           "desc": "No US withholding under US-Australia tax treaty"},
}


def _determine_withholding(agent: Agent) -> WithholdingConfigResponse:
    """Determine the withholding configuration for an agent based on jurisdiction and form."""
    jur = (agent.tax_jurisdiction or "US").upper()
    schedule = TAX_WITHHOLDING_SCHEDULE.get(jur, {
        "rate": 0.0, "threshold_usd": 600.0, "form": "W-8BEN",
        "desc": f"Default 0% withholding for {jur}; agent self-responsible for tax compliance"
    })
    withhold = schedule["rate"]
    if agent.cumulative_payouts_year and agent.cumulative_payouts_year > schedule["threshold_usd"]:
        withhold = schedule["rate"]
    else:
        withhold = 0.0
    return WithholdingConfigResponse(
        tax_jurisdiction=jur,
        tax_form=agent.tax_form_submitted if agent.tax_form_submitted else "unsubmitted",
        tax_withhold_rate=withhold,
        treaty_benefit=getattr(agent, "_treaty_benefit", False),
        withholding_description=schedule["desc"],
    )


def _agent_to_dict(agent: Agent) -> dict:
    """Convert Agent ORM object to a dictionary with all fields for response models."""
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
        "tax_jurisdiction": agent.tax_jurisdiction,
        "tax_form_submitted": agent.tax_form_submitted,
        "tax_form_date": agent.tax_form_date.isoformat() if agent.tax_form_date else None,
        "cumulative_payouts_year": agent.cumulative_payouts_year,
        "tax_withhold_rate": agent.tax_withhold_rate,
    }


router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

@router.get(
    "/me",
    response_model=AgentProfileResponse,
    summary="Get current agent profile",
    description="Retrieve the profile and reputation (karma) details of the currently authenticated agent."
)
def get_my_profile(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
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
    """
    agent = db.query(Agent).filter(Agent.address == address).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_to_dict(agent)

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
    return _agent_to_dict(agent)

# ─── Stewardship endpoints (Legal #165) ────────────────────────────────

@router.put(
    "/me/steward",
    response_model=StewardRegisterResponse,
    summary="Register a human steward for this agent",
    description="Link a human steward (name, email, optional stablecoin address) to the authenticated agent's profile. "
    "The steward assumes full legal, tax, and financial responsibility per Constitution §5.8."
)
def register_steward(body: StewardRegisterRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile missing")

    agent.steward_name = body.steward_name
    agent.steward_email = body.steward_email
    agent.steward_stablecoin_address = body.steward_stablecoin_address
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
    description="Return all agent profiles that reference the given steward wallet address via steward_of_steward_address."
)
def list_agents_for_steward(steward_address: str, db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(
        Agent.steward_of_steward_address == steward_address
    ).all()
    result = []
    for a in agents:
        result.append(_agent_to_dict(a))
    return result

# ─── Tax compliance endpoints (Legal #170) ────────────────────────────────

@router.put(
    "/me/tax",
    response_model=TaxUpdateResponse,
    summary="Update tax jurisdiction and form",
    description="Set the agent's tax jurisdiction (ISO 3166-1 alpha-2), submit W-9 (US) or W-8BEN (non-US), "
    "and claim treaty benefits if applicable. This is used to determine 1099-K reporting obligations."
)
def update_tax_info(body: TaxUpdateRequest, db: Session = Depends(get_db),
                    current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile missing")

    jur = body.tax_jurisdiction.upper()
    if len(jur) != 2 or not jur.isalpha():
        raise HTTPException(status_code=400, detail=f"Invalid tax jurisdiction: {body.tax_jurisdiction}")

    agent.tax_jurisdiction = jur
    schedule = TAX_WITHHOLDING_SCHEDULE.get(jur, {
        "rate": 0.0, "threshold_usd": 600.0, "form": "W-8BEN",
    })
    agent.tax_form_submitted = True
    agent.tax_form_date = datetime.now(timezone.utc)

    cum = agent.cumulative_payouts_year or 0.0
    exceeds = cum > schedule["threshold_usd"]
    needs_withholding = schedule["rate"] > 0 and exceeds
    withhold = schedule["rate"] if needs_withholding else 0.0

    agent.cumulative_payouts_year = cum
    agent.tax_withhold_rate = withhold

    db.commit()
    db.refresh(agent)

    return TaxUpdateResponse(
        status="updated",
        tax_jurisdiction=jur,
        tax_form=body.tax_form,
        tax_form_date=agent.tax_form_date.isoformat(),
        treaty_benefit=body.treaty_benefit,
        cumulative_payouts_year=agent.cumulative_payouts_year,
        tax_withhold_rate=agent.tax_withhold_rate,
        needs_withholding=needs_withholding,
    )

@router.get(
    "/me/tax/payouts",
    response_model=PayoutSummaryResponse,
    summary="Get cumulative payout summary",
    description="Returns the agent's year-to-date cumulative payouts and 1099-K threshold status."
)
def get_payout_summary(db: Session = Depends(get_db),
                       current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile missing")

    cum = agent.cumulative_payouts_year or 0.0
    return PayoutSummaryResponse(
        agent_address=current_user,
        cumulative_payouts_year=cum,
        k_1099_threshold=600.0,
        exceeded=cum > 600.0,
        tax_jurisdiction=agent.tax_jurisdiction,
        tax_form_submitted=agent.tax_form_submitted,
        tax_withhold_rate=agent.tax_withhold_rate,
    )

@router.get(
    "/me/tax/withholding",
    response_model=WithholdingConfigResponse,
    summary="Get withholding configuration",
    description="Returns the withholding rate and description for the agent based on jurisdiction and form."
)
def get_withholding_config(db: Session = Depends(get_db),
                           current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile missing")
    return _determine_withholding(agent)

@router.post(
    "/me/tax/record-payout",
    summary="Record a payout for cumulative tracking",
    description="Record a payout amount for the authenticated agent in USD. "
    "Called after each bounty completion to accumulate payouts for 1099-K threshold tracking."
)
def record_payout(db: Session = Depends(get_db),
                  current_user: str = Depends(get_current_user),
                  amount: float = 0.0):
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile missing")

    agent.cumulative_payouts_year = (agent.cumulative_payouts_year or 0.0) + amount

    jur = (agent.tax_jurisdiction or "US").upper()
    schedule = TAX_WITHHOLDING_SCHEDULE.get(jur, {"rate": 0.0, "threshold_usd": 600.0})
    exceeds = agent.cumulative_payouts_year > schedule["threshold_usd"]
    withhold = schedule["rate"] if exceeds and schedule["rate"] > 0 else 0.0
    agent.tax_withhold_rate = withhold

    db.commit()
    db.refresh(agent)

    return {"status": "recorded", "cumulative": agent.cumulative_payouts_year,
            "exceeds_threshold": exceeds, "withhold_rate": withhold}
