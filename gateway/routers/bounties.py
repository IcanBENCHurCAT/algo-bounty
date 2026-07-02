import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from ..database import Bounty, Agent, GitHubPR, Notification
from ..auth import get_current_user
from ..dependencies import get_db
from ..schemas import BountyCreate
from ..broker import broker
from ..algod_client import (
    get_algod_client, get_default_account,
    is_sandbox, compile_escrow_contract,
)

router = APIRouter(prefix="/api/v1/bounties", tags=["bounties"])
sandbox_active = is_sandbox()

@router.get("")
def list_bounties(
    status: Optional[str] = None,
    repo: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    min_karma: Optional[int] = None,
    hitm: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Bounty)
    if status:
        query = query.filter(Bounty.status == status)
    if repo:
        # Escape wildcards to prevent Unbounded LIKE Query (SQL Injection Variant)
        escaped_repo = repo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(Bounty.repo_url.contains(escaped_repo, escape="\\"))
    if min_amount is not None:
        query = query.filter(Bounty.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Bounty.amount <= max_amount)
    if min_karma is not None:
        query = query.filter(Bounty.karma_requirement >= min_karma)
    if hitm is not None:
        query = query.filter(Bounty.is_hitm == hitm)

    bounties = query.all()
    # Serialize
    result = []
    for b in bounties:
        result.append({
            "bounty_id": b.bounty_id,
            "app_id": b.app_id,
            "status": b.status,
            "creator": b.creator,
            "worker": b.worker,
            "amount": b.amount,
            "asset_id": b.asset_id,
            "asset_name": "ALGO" if b.asset_id == 0 else f"ASA-{b.asset_id}",
            "hitm": b.is_hitm,
            "description": b.description,
            "repo_url": b.repo_url,
            "karma_requirement": b.karma_requirement,
            "created_at": b.created_at.isoformat() + "Z",
            "rejection_count": b.rejection_count
        })
    return {"bounties": result, "total": len(result)}

@router.get("/{bounty_id}")
def get_bounty(bounty_id: str, db: Session = Depends(get_db)):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    return {
        "bounty_id": b.bounty_id,
        "app_id": b.app_id,
        "status": b.status,
        "creator": b.creator,
        "worker": b.worker,
        "amount": b.amount,
        "asset_id": b.asset_id,
        "asset_name": "ALGO" if b.asset_id == 0 else f"ASA-{b.asset_id}",
        "hitm": b.is_hitm,
        "description": b.description,
        "repo_url": b.repo_url,
        "karma_requirement": b.karma_requirement,
        "created_at": b.created_at.isoformat() + "Z",
        "rejection_count": b.rejection_count
    }

@router.post("")
def create_bounty(body: BountyCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    # Check if user has enough karma to create this bounty
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=403, detail="Agent profile missing")

    bounty_id = f"b_{int(datetime.utcnow().timestamp())}"

    # Deploy escrow contract on-chain (if on a live network)
    app_id = None
    tx_id = None
    onchain = False

    if not sandbox_active:
        try:
            client = get_algod_client()

            # Compile the escrow contract
            teal = compile_escrow_contract()
            compile_resp = client.compile(teal, format="teal")
            compiled_program = compile_resp.get("result", "").encode()

            if compiled_program:
                params = client.suggested_params()

                # Encode app args
                from algosdk.abi import ABIType
                bounty_id_bytes = body.description[:64].encode()
                escrow_amount = int(body.amount * 1_000_000)
                asset_id = int(body.asset_id)
                is_hitm = 1 if body.hitm else 0

                app_args = ABIType.from_string(
                    "(bytes,uint64,uint64,uint64)"
                ).encode(
                    bounty_id_bytes, escrow_amount, is_hitm, asset_id
                )

                platform_account = get_default_account()
                if platform_account is None:
                    raise HTTPException(
                        status_code=500,
                        detail="PLATFORM_PRIVATE_KEY not configured"
                    )

                from algosdk.transaction import ApplicationCreateTxn, OnComplete
                create_txn = ApplicationCreateTxn(
                    sender=platform_account.address,
                    sp=params,
                    on_complete=OnComplete.NoOpOC,
                    app_args=[app_args],
                    program=compiled_program,
                    approval_program=compiled_program,
                    clear_program=compiled_program,
                )

                signed_txn = create_txn.sign(platform_account.private_key)
                tx_id = client.send_transaction([signed_txn])

                # Wait for confirmation
                from algosdk.waiting import wait_for_confirmation
                pending_info = wait_for_confirmation(client, tx_id, 4)
                if pending_info:
                    app_id = pending_info.get("application-index")
                    onchain = app_id is not None and app_id > 0

        except Exception as e:
            print(f"[WEB3] Escrow deploy failed: {e}")
            app_id = None
            onchain = False

    # Create DB record (always works, on-chain or not)
    new_bounty = Bounty(
        bounty_id=bounty_id,
        app_id=app_id,
        status="open",
        creator=current_user,
        amount=body.amount,
        asset_id=body.asset_id,
        is_hitm=body.hitm,
        description=body.description,
        repo_url=body.repo_url,
        karma_requirement=body.karma_requirement,
        hitm_review_days=body.hitm_review_days
    )
    db.add(new_bounty)
    db.commit()
    db.refresh(new_bounty)

    # Broadcast event
    broker.publish("bounty.created", {
        "bounty_id": bounty_id,
        "app_id": app_id,
        "amount": body.amount,
        "creator": current_user,
        "onchain": onchain,
    })

    return {
        "bounty_id": bounty_id,
        "app_id": app_id,
        "status": "open",
        "tx_id": tx_id,
        "onchain": onchain,
    }

@router.post("/{bounty_id}/claim")
def claim_bounty(bounty_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.status != "open":
        raise HTTPException(status_code=400, detail="Bounty not claimable")
    if b.creator == current_user:
        raise HTTPException(status_code=400, detail="Cannot claim your own bounty")

    # Check worker karma requirement
    worker = db.query(Agent).filter(Agent.address == current_user).first()
    if not worker or worker.karma < b.karma_requirement:
        raise HTTPException(status_code=403, detail=f"Insufficient karma. Required: {b.karma_requirement}")

    b.status = "claimed"
    b.worker = current_user
    db.commit()

    broker.publish("bounty.claimed", {
        "bounty_id": bounty_id,
        "worker": current_user
    })

    # Create notification for creator
    notif = Notification(
        recipient=b.creator,
        message=f"Your bounty {bounty_id} has been claimed by {current_user}!"
    )
    db.add(notif)
    db.commit()

    return {"bounty_id": bounty_id, "status": "claimed", "worker": current_user}

@router.post("/{bounty_id}/submit")
def submit_work(
    bounty_id: str,
    pr_url: str = Body(..., embed=True),
    proof_data: dict = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.status != "claimed":
        raise HTTPException(status_code=400, detail="Bounty must be claimed to submit work")
    if b.worker != current_user:
        raise HTTPException(status_code=403, detail="Only the claiming worker can submit work")

    b.status = "submitted"
    db.commit()

    # Link PR
    # Match PR number if available
    pr_num_match = re.search(r'pull/(\d+)', pr_url)
    pr_number = int(pr_num_match.group(1)) if pr_num_match else 1

    new_pr = GitHubPR(
        pr_number=pr_number,
        repo_url=b.repo_url,
        bounty_id=bounty_id,
        state="open",
        author=current_user
    )
    db.add(new_pr)

    # Create notification for creator
    notif = Notification(
        recipient=b.creator,
        message=f"Bounty {bounty_id} work submitted by {current_user}! Review required."
    )
    db.add(notif)
    db.commit()

    broker.publish("bounty.submitted", {
        "bounty_id": bounty_id,
        "worker": current_user,
        "pr_url": pr_url
    })

    return {"bounty_id": bounty_id, "status": "submitted"}

@router.post("/{bounty_id}/approve")
def approve_work(bounty_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.creator != current_user:
        raise HTTPException(status_code=403, detail="Only creator can approve work")
    if b.status != "submitted":
        raise HTTPException(status_code=400, detail="Bounty has no work submitted to approve")

    b.status = "closed"
    b.payout_type = "PAYOUT"
    db.commit()

    # Adjust worker karma (+5)
    worker = db.query(Agent).filter(Agent.address == b.worker).first()
    if worker:
        worker.karma += 5
        worker.completed_bounties += 1
        db.commit()

    broker.publish("bounty.approved", {
        "bounty_id": bounty_id,
        "worker": b.worker
    })

    # Notify worker
    notif = Notification(
        recipient=b.worker,
        message=f"Your submission for bounty {bounty_id} has been APPROVED! Funds released."
    )
    db.add(notif)
    db.commit()

    return {"bounty_id": bounty_id, "status": "closed", "payout_type": "PAYOUT"}

@router.post("/{bounty_id}/reject")
def reject_work(
    bounty_id: str,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.creator != current_user:
        raise HTTPException(status_code=403, detail="Only creator can reject work")
    if b.status != "submitted":
        raise HTTPException(status_code=400, detail="No work submitted to reject")

    b.status = "rejected"
    b.rejection_count += 1
    db.commit()

    # Notify worker
    notif = Notification(
        recipient=b.worker,
        message=f"Your submission for bounty {bounty_id} has been REJECTED. Reason: {reason}"
    )
    db.add(notif)
    db.commit()

    broker.publish("bounty.rejected", {
        "bounty_id": bounty_id,
        "worker": b.worker,
        "reason": reason
    })

    return {"bounty_id": bounty_id, "status": "rejected", "rejection_count": b.rejection_count}

@router.post("/{bounty_id}/dispute")
def dispute_work(
    bounty_id: str,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if current_user not in [b.creator, b.worker]:
        raise HTTPException(status_code=403, detail="Only bounty participants can open a dispute")
    if b.status not in ["submitted", "rejected"]:
        raise HTTPException(status_code=400, detail="Cannot dispute at this stage")

    b.status = "disputed"
    db.commit()

    # Notify other party
    other_party = b.worker if current_user == b.creator else b.creator
    notif = Notification(
        recipient=other_party,
        message=f"Bounty {bounty_id} has been placed in DISPUTE by {current_user}. Reason: {reason}"
    )
    db.add(notif)
    db.commit()

    broker.publish("bounty.disputed", {
        "bounty_id": bounty_id,
        "initiator": current_user,
        "reason": reason
    })

    return {"bounty_id": bounty_id, "status": "disputed"}

@router.get("/{bounty_id}/onchain")
def get_bounty_onchain(bounty_id: str, db: Session = Depends(get_db)):
    """Poll on-chain escrow state for a bounty."""
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b or not b.app_id:
        return {"bounty_id": bounty_id, "onchain": False, "status": "pending"}

    try:
        client = get_algod_client()
        app_info = client.application_info(b.app_id)
        return {
            "bounty_id": bounty_id,
            "onchain": True,
            "app_id": b.app_id,
            "confirmed_round": app_info.get("last-round", 0),
            "state": "escrow_active",
        }
    except Exception as e:
        return {
            "bounty_id": bounty_id,
            "onchain": False,
            "error": str(e),
            "status": b.status,
        }
