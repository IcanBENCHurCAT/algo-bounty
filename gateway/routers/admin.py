from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

from ..database import Bounty, Agent, AccountQuarantine
from ..dependencies import get_db
from ..auth import is_admin
from ..schemas import AdminResolveRequest, AdminResolveResponse
from ..config import settings
from ..broker import broker

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class QuarantineResolveRequest(BaseModel):
    action: str  # "clear" or "penalize"
    resolution_note: Optional[str] = "Admin review completed"
    karma_penalty: Optional[int] = 0


@router.post("/disputes/{bounty_id}/resolve", response_model=AdminResolveResponse, summary="Admin Resolve Dispute")
def admin_resolve_dispute(
    bounty_id: str,
    body: AdminResolveRequest,
    db: Session = Depends(get_db),
    admin_user: str = Depends(is_admin)
):
    bounty = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if bounty.status != "disputed":
        raise HTTPException(status_code=400, detail="Bounty is not in disputed state")

    res_val = body.resolution.lower()
    if res_val not in ["worker_win", "creator_win", "split"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid resolution option. Must be worker_win, creator_win, or split"
        )

    # Apply DB resolution state
    bounty.status = "closed"
    if res_val == "worker_win":
        bounty.payout_type = "PAYOUT"
        worker_agent = db.query(Agent).filter(Agent.address == bounty.worker).first() if bounty.worker else None
        if worker_agent:
            worker_agent.karma += 5
            worker_agent.completed_bounties += 1
    elif res_val == "creator_win":
        bounty.payout_type = "REFUND"
    else:
        bounty.payout_type = "SPLIT"

    db.commit()

    broker.publish("admin.dispute_resolved", {
        "bounty_id": bounty_id,
        "admin": admin_user,
        "resolution": res_val,
        "reason": body.reason
    })

    return {
        "status": "resolved",
        "bounty_id": bounty_id,
        "resolution": res_val,
        "tx_id": "ADMIN_OVERRIDE",
        "message": f"Dispute on bounty {bounty_id} resolved as {res_val} by admin."
    }


@router.get("/quarantines", summary="List Quarantined Accounts")
def list_quarantines(
    status: Optional[str] = "active",
    db: Session = Depends(get_db),
    admin_user: str = Depends(is_admin)
):
    query = db.query(AccountQuarantine)
    if status:
        query = query.filter(AccountQuarantine.status == status)
    records = query.all()
    return {
        "quarantines": [
            {
                "id": q.id,
                "address": q.address,
                "reason": q.reason,
                "details": q.details,
                "quarantined_at": q.quarantined_at.isoformat(),
                "expires_at": q.expires_at.isoformat(),
                "status": q.status,
                "resolved_by": q.resolved_by,
                "resolved_at": q.resolved_at.isoformat() if q.resolved_at else None,
                "resolution_note": q.resolution_note
            }
            for q in records
        ],
        "total": len(records)
    }


@router.post("/quarantines/{quarantine_id}/resolve", summary="Resolve Account Quarantine")
def resolve_quarantine(
    quarantine_id: int,
    body: QuarantineResolveRequest,
    db: Session = Depends(get_db),
    admin_user: str = Depends(is_admin)
):
    q = db.query(AccountQuarantine).filter(AccountQuarantine.id == quarantine_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quarantine record not found")

    action = body.action.lower()
    if action not in ["clear", "penalize"]:
        raise HTTPException(status_code=400, detail="Action must be clear or penalize")

    q.status = "cleared" if action == "clear" else "penalized"
    q.resolved_by = admin_user
    q.resolved_at = datetime.now(timezone.utc)
    q.resolution_note = body.resolution_note

    if action == "penalize" and body.karma_penalty > 0:
        agent = db.query(Agent).filter(Agent.address == q.address).first()
        if agent:
            agent.karma = max(0, agent.karma - body.karma_penalty)

    db.commit()

    return {
        "status": q.status,
        "quarantine_id": quarantine_id,
        "address": q.address,
        "action": action,
        "message": f"Quarantine for {q.address} updated to {q.status}."
    }
