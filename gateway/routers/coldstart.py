"""
Cold-start support for new agents (Karma #175).

Two bootstrapping mechanisms:
1. Collateral staking — new agents lock ALGO as temporary reputation proxy
2. Co-signing vouch — Elite agents vouch for newcomers with partial reputation risk

When both are available, well-funded newcomers can participate trustlessly via
collateral, while community-driven trust building happens via co-signing.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import Agent, Bounty, CollateralDeposit, Vouch
from ..auth import get_current_user
from ..dependencies import get_db
from ..schemas import BountyCreateResponse

router = APIRouter(prefix="/api/v1/cold-start", tags=["cold-start"])


# ─── Collateral Deposit Endpoints ───────────────────────────────────

@router.post("/deposit")
def deposit_collateral(
    amount_microalgo: int = Query(..., ge=1_000_000, description="Minimum 1 ALGO (1,000,000 microalgo)"),
    bounty_id: Optional[str] = Query(None, description="Optional: associate collateral with a specific bounty"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Lock ALGO as temporary reputation for a new/low-karma agent.

    The collateral serves as a financial guarantee — if the agent's bounty
    fails in dispute, the locked ALGO is slashed (burned to the vault).
    If the bounty succeeds, the collateral is returned plus a small bonus.
    """
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check for existing active collateral
    existing = (
        db.query(CollateralDeposit)
        .filter(CollateralDeposit.agent_address == current_user, CollateralDeposit.status == "locked")
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Agent already has {existing.amount_microalgo} microalgo locked as collateral. "
            f"Release it first or contact admin to increase stake.",
        )

    deposit = CollateralDeposit(
        agent_address=current_user,
        amount_microalgo=amount_microalgo,
        bounty_id=bounty_id,
        status="locked",
        created_at=datetime.now(timezone.utc),
    )
    db.add(deposit)

    # Update agent flags
    agent.has_collateral = True

    # If collateral >= 5 ALGO (5M microalgo), grant +10 karma as incentive
    if amount_microalgo >= 5_000_000:
        agent.karma += 10
        db.commit()
        db.refresh(agent)

    db.commit()
    db.refresh(deposit)

    return {
        "status": "deposited",
        "deposit_id": deposit.id,
        "amount_microalgo": amount_microalgo,
        "amount_algo": amount_microalgo / 1_000_000,
        "bounty_id": deposit.bounty_id,
        "agent_has_collateral": True,
        "karma_adjustment": 10 if amount_microalgo >= 5_000_000 else 0,
        "released_at": deposit.released_at.isoformat() if deposit.released_at else None,
    }


@router.get("/my-deposits")
def get_my_collateral_deposits(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List all collateral deposits for the current agent."""
    deposits = (
        db.query(CollateralDeposit)
        .filter(CollateralDeposit.agent_address == current_user)
        .order_by(CollateralDeposit.created_at.desc())
        .all()
    )

    return {
        "deposits": [
            {
                "id": d.id,
                "amount_algo": d.amount_microalgo / 1_000_000,
                "status": d.status,
                "bounty_id": d.bounty_id,
                "created_at": d.created_at.isoformat(),
                "released_at": d.released_at.isoformat() if d.released_at else None,
            }
            for d in deposits
        ]
    }


# ─── Vouch Endpoints ───────────────────────────────────────────────

@router.post("/vouch")
def create_vouch(
    vouched_agent: str = Query(..., description="Address of the agent being vouched for"),
    bounty_id: Optional[str] = Query(None, description="Optional: associate vouch with a specific bounty"),
    amount_at_stake: int = Query(
        default=1_000_000,
        ge=100_000,
        description="Reputation capital at stake (microalgo). Default: 1 ALGO equivalent."
    ),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Elite agent co-signs a new agent's bounty.

    The vouching agent takes partial reputation risk — if the new agent
    performs well, both gain karma. If the new agent fails, the vouching
    agent loses more.
    """
    vouching = db.query(Agent).filter(Agent.address == current_user).first()
    vouched = db.query(Agent).filter(Agent.address == vouched_agent).first()

    if not vouching:
        raise HTTPException(status_code=404, detail="Vouching agent not found")
    if not vouched:
        raise HTTPException(status_code=404, detail="Vouched agent not found")

    if vouching.address == vouched.address:
        raise HTTPException(status_code=400, detail="Cannot vouch for yourself")

    # Check for existing active vouch
    existing = (
        db.query(Vouch)
        .filter(Vouch.vouching_agent == current_user, Vouch.vouched_agent == vouched_agent, Vouch.status == "active")
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Agent {vouched_agent} already has an active vouch from you.",
        )

    vouch = Vouch(
        vouching_agent=current_user,
        vouched_agent=vouched_agent,
        bounty_id=bounty_id,
        amount_at_stake=amount_at_stake,
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db.add(vouch)

    # Update vouched agent's vouch count
    vouched.vouched_by_count += 1

    # If vouching agent has >= 25 karma (Elite), grant +5 karma for vouching
    if vouching.karma >= 25:
        vouching.karma += 5
        db.commit()
        db.refresh(vouching)

    db.commit()
    db.refresh(vouch)

    return {
        "status": "vouched",
        "vouch_id": vouch.id,
        "vouching_agent": vouch.vouching_agent,
        "vouched_agent": vouch.vouched_agent,
        "amount_at_stake_algo": amount_at_stake / 1_000_000,
        "bounty_id": vouch.bounty_id,
        "vouched_agent_vouch_count": vouched.vouched_by_count,
        "vouching_karma_bonus": 5 if vouching.karma >= 25 else 0,
        "resolved_at": vouch.resolved_at.isoformat() if vouch.resolved_at else None,
    }


@router.get("/my-vouches")
def get_my_vouches(
    role: str = Query("vouched", description="View vouches where I am 'vouched' or 'vouching'"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List vouches involving the current agent."""
    if role == "vouched":
        vouches = (
            db.query(Vouch)
            .filter(Vouch.vouched_agent == current_user)
            .order_by(Vouch.created_at.desc())
            .all()
        )
    elif role == "vouching":
        vouches = (
            db.query(Vouch)
            .filter(Vouch.vouching_agent == current_user)
            .order_by(Vouch.created_at.desc())
            .all()
        )
    else:
        raise HTTPException(status_code=400, detail="role must be 'vouched' or 'vouching'")

    return {
        "vouches": [
            {
                "id": v.id,
                "vouching_agent": v.vouching_agent,
                "vouched_agent": v.vouched_agent,
                "amount_at_stake_algo": v.amount_at_stake / 1_000_000,
                "status": v.status,
                "bounty_id": v.bounty_id,
                "created_at": v.created_at.isoformat(),
                "resolved_at": v.resolved_at.isoformat() if v.resolved_at else None,
            }
            for v in vouches
        ]
    }


# ─── Release Vouches ───────────────────────────────────────────────

@router.post("/vouch/{vouch_id}/resolve")
def resolve_vouch(
    vouch_id: int,
    outcome: str = Query(..., description="'resolved', 'slashed', or 'expired'"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Resolve a vouch after its associated bounty is complete.

    - resolved: both parties gain karma
    - slashed: vouching agent loses their stake
    - expired: vouch timed out without resolution
    """
    vouch = db.query(Vouch).filter(Vouch.id == vouch_id).first()
    if not vouch:
        raise HTTPException(status_code=404, detail="Vouch not found")
    if vouch.status != "active":
        raise HTTPException(status_code=400, detail=f"Vouch already {vouch.status}")

    vouch.status = outcome
    vouch.resolved_at = datetime.now(timezone.utc)

    # Apply karma adjustments based on outcome
    vouching = db.query(Agent).filter(Agent.address == vouch.vouching_agent).first()
    vouched = db.query(Agent).filter(Agent.address == vouch.vouched_agent).first()

    if outcome == "resolved":
        if vouching:
            vouching.karma += 5
        if vouched:
            vouched.karma += 3
    elif outcome == "slashed":
        if vouching:
            # Lose amount_at_stake equivalent in karma
            vouching.karma = max(0, vouching.karma - (vouch.amount_at_stake // 1_000_000))
        if vouched:
            vouched.karma -= 1

    db.commit()
    db.refresh(vouch)

    return {
        "status": "resolved",
        "vouch_id": vouch.id,
        "outcome": outcome,
        "vouching_karma_change": 5 if outcome == "resolved" else -(vouch.amount_at_stake // 1_000_000) if outcome == "slashed" else 0,
        "vouched_karma_change": 3 if outcome == "resolved" else (-1 if outcome == "slashed" else 0),
    }


# ─── Release Collateral ────────────────────────────────────────────

@router.post("/deposit/{deposit_id}/release")
def release_collateral(
    deposit_id: int,
    outcome: str = Query(..., description="'released' (success) or 'slashed' (failure)"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Release collateral after its associated bounty is resolved.

    - released: agent gets their ALGO back plus bonus
    - slashed: collateral is lost (agent failed to deliver)
    """
    deposit = db.query(CollateralDeposit).filter(
        CollateralDeposit.id == deposit_id,
        CollateralDeposit.agent_address == current_user,
        CollateralDeposit.status == "locked",
    ).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found or not locked")

    deposit.status = outcome
    deposit.released_at = datetime.now(timezone.utc)

    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if outcome == "released":
        # Agent gets ALGO back + 5% bonus
        bonus = deposit.amount_microalgo * 5 // 100
        agent.karma += 15  # bonus karma for successful collateral path

        # Update agent flags
        active_collateral = (
            db.query(CollateralDeposit)
            .filter(
                CollateralDeposit.agent_address == current_user,
                CollateralDeposit.status == "locked",
            )
            .first()
        )
        if not active_collateral:
            agent.has_collateral = False

    elif outcome == "slashed":
        agent.karma -= 5

    db.commit()
    db.refresh(deposit)

    return {
        "status": outcome,
        "deposit_id": deposit.id,
        "amount_microalgo": deposit.amount_microalgo,
        "agent_karma_change": 15 if outcome == "released" else -5,
        "agent_has_collateral": agent.has_collateral,
        "released_at": deposit.released_at.isoformat() if deposit.released_at else None,
    }


# ─── Cold-Start Status Endpoint ────────────────────────────────────

@router.get("/status/{address}")
def get_coldstart_status(
    address: str,
    db: Session = Depends(get_db),
):
    """Get cold-start eligibility and status for any agent."""
    agent = db.query(Agent).filter(Agent.address == address).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    active_collateral = (
        db.query(CollateralDeposit)
        .filter(CollateralDeposit.agent_address == address, CollateralDeposit.status == "locked")
        .first()
    )
    active_vouches = (
        db.query(Vouch)
        .filter(Vouch.vouched_agent == address, Vouch.status == "active")
        .all()
    )
    vouches_given = (
        db.query(Vouch)
        .filter(Vouch.vouching_agent == address, Vouch.status == "active")
        .all()
    )

    cold_start_eligible = agent.karma == 0 or not agent.has_collateral or agent.cold_start_eligible
    can_create_bounties = agent.karma > 0 or bool(active_collateral) or bool(active_vouches)

    return {
        "address": address,
        "karma": agent.karma,
        "completed_bounties": agent.completed_bounties,
        "has_collateral": agent.has_collateral,
        "active_collateral_amount": active_collateral.amount_microalgo / 1_000_000 if active_collateral else 0,
        "active_vouches_count": len(active_vouches),
        "vouches_given_count": len(vouches_given),
        "cold_start_eligible": cold_start_eligible,
        "can_create_bounties": can_create_bounties,
    }
