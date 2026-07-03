import re
from datetime import datetime, UTC
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from ..database import Bounty, Agent, GitHubPR, Notification
from ..auth import get_current_user
from ..dependencies import get_db
from ..schemas import (
    BountyCreate, BountyClaim, WorkSubmit,
    WorkApprove, WorkReject, DisputeCreate
)
from ..broker import broker
from ..algod_client import (
    get_algod_client, get_default_account,
    is_sandbox, compile_escrow_contract,
    send_signed_transaction,
)

router = APIRouter(prefix="/api/v1/bounties", tags=["bounties"])
sandbox_active = is_sandbox()

@router.get("", summary="List all bounties", description="Retrieve a list of bounties with optional filtering by status, repository, amount, karma requirement, and HITM mode.")
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
            "created_at": b.created_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            "rejection_count": b.rejection_count
        })
    return {"bounties": result, "total": len(result)}

@router.get("/{bounty_id}", summary="Get bounty details", description="Retrieve detailed information about a specific bounty by its ID.")
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
        "created_at": b.created_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "rejection_count": b.rejection_count
    }

@router.post("", summary="Create a new bounty", description="Deploy a new bounty escrow on-chain (if not in sandbox) and create a database record. Deducts 1 karma from the creator.")
def create_bounty(body: BountyCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    # Check if user has enough karma to create this bounty
    agent = db.query(Agent).filter(Agent.address == current_user).first()
    if not agent:
        raise HTTPException(status_code=403, detail="Agent profile missing")

    # Karma System: Deduct 1 karma for creating a bounty (v2 scoring rules)
    agent.karma -= 1
    db.commit()

    bounty_id = f"b_{int(datetime.now(UTC).timestamp())}"

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
                review_days = int(body.hitm_review_days)

                app_args = ABIType.from_string(
                    "(bytes,uint64,uint64,uint64,uint64)"
                ).encode(
                    bounty_id_bytes, escrow_amount, is_hitm, asset_id, review_days
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

@router.post("/{bounty_id}/claim", summary="Claim a bounty", description="Allows a worker to claim an open bounty. Validates karma requirements and processes on-chain claim if a signed transaction is provided.")
def claim_bounty(
    bounty_id: str,
    body: BountyClaim,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
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

    # Broadcase on-chain transaction
    tx_id = None
    if body.signed_txn:
        try:
            tx_id = send_signed_transaction(body.signed_txn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"On-chain transaction failed: {e}")

    b.status = "claimed"
    b.worker = current_user
    db.commit()

    broker.publish("bounty.claimed", {
        "bounty_id": bounty_id,
        "worker": current_user,
        "tx_id": tx_id
    })

    # Create notification for creator
    notif = Notification(
        recipient=b.creator,
        message=f"Your bounty {bounty_id} has been claimed by {current_user}!"
    )
    db.add(notif)
    db.commit()

    return {"bounty_id": bounty_id, "status": "claimed", "worker": current_user, "tx_id": tx_id}

@router.post("/{bounty_id}/submit", summary="Submit work for a bounty", description="Allows the claiming worker to submit their solution (PR URL). Updates bounty status to 'submitted'.")
def submit_work(
    bounty_id: str,
    body: WorkSubmit,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.status != "claimed" and b.status != "rejected":
        raise HTTPException(status_code=400, detail="Bounty state must be claimed or rejected to submit work")
    if b.worker != current_user:
        raise HTTPException(status_code=403, detail="Only the claiming worker can submit work")

    # Broadcast on-chain transaction
    tx_id = None
    if body.signed_txn:
        try:
            tx_id = send_signed_transaction(body.signed_txn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"On-chain transaction failed: {e}")

    b.status = "submitted"
    db.commit()

    # Link PR
    # Match PR number if available
    pr_num_match = re.search(r'pull/(\d+)', body.pr_url)
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
        "pr_url": body.pr_url,
        "tx_id": tx_id
    })

    return {"bounty_id": bounty_id, "status": "submitted", "tx_id": tx_id}

@router.post("/{bounty_id}/approve", summary="Approve submitted work", description="Allows the creator to approve the submitted work, closing the bounty and releasing funds. Awards +10 karma to worker and +5 to creator.")
def approve_work(
    bounty_id: str,
    body: WorkApprove,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.creator != current_user:
        raise HTTPException(status_code=403, detail="Only creator can approve work")
    if b.status != "submitted":
        raise HTTPException(status_code=400, detail="Bounty has no work submitted to approve")

    # Broadcast on-chain transaction
    tx_id = None
    if body.signed_txn:
        try:
            tx_id = send_signed_transaction(body.signed_txn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"On-chain transaction failed: {e}")

    b.status = "closed"
    b.payout_type = "PAYOUT"
    db.commit()

    # Adjust karma (v2 rules: +10 to worker, +5 to creator)
    worker = db.query(Agent).filter(Agent.address == b.worker).first()
    if worker:
        worker.karma += 10
        worker.completed_bounties += 1

    creator = db.query(Agent).filter(Agent.address == b.creator).first()
    if creator:
        creator.karma += 5
    db.commit()

    broker.publish("bounty.approved", {
        "bounty_id": bounty_id,
        "worker": b.worker,
        "tx_id": tx_id
    })

    # Notify worker
    notif = Notification(
        recipient=b.worker,
        message=f"Your submission for bounty {bounty_id} has been APPROVED! Funds released."
    )
    db.add(notif)
    db.commit()

    return {"bounty_id": bounty_id, "status": "closed", "payout_type": "PAYOUT", "tx_id": tx_id}

@router.post("/{bounty_id}/reject", summary="Reject submitted work", description="Allows the creator to reject submitted work. Increments rejection count and applies progressive karma penalties to the worker.")
def reject_work(
    bounty_id: str,
    body: WorkReject,
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

    # Broadcast on-chain transaction
    tx_id = None
    if body.signed_txn:
        try:
            tx_id = send_signed_transaction(body.signed_txn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"On-chain transaction failed: {e}")

    b.status = "rejected"
    b.rejection_count += 1
    db.commit()

    # Karma System: Deduct karma from worker for rejection (v2 rules)
    # -1 for 1st, -2 for 2nd, -5 for 3rd rejection
    worker = db.query(Agent).filter(Agent.address == b.worker).first()
    if worker:
        penalty = 0
        if b.rejection_count == 1:
            penalty = 1
        elif b.rejection_count == 2:
            penalty = 2
        elif b.rejection_count >= 3:
            penalty = 5
        worker.karma -= penalty
        db.commit()

    # Notify worker
    notif = Notification(
        recipient=b.worker,
        message=f"Your submission for bounty {bounty_id} has been REJECTED. Reason: {body.reason}"
    )
    db.add(notif)
    db.commit()

    broker.publish("bounty.rejected", {
        "bounty_id": bounty_id,
        "worker": b.worker,
        "reason": body.reason,
        "tx_id": tx_id
    })

    return {"bounty_id": bounty_id, "status": "rejected", "rejection_count": b.rejection_count, "tx_id": tx_id}

@router.post("/{bounty_id}/dispute", summary="Open a dispute", description="Allows either the creator or the worker to open a dispute if the work is in submitted or rejected state.")
def dispute_work(
    bounty_id: str,
    body: DisputeCreate,
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

    # Broadcast on-chain transaction
    tx_id = None
    if body.signed_txn:
        try:
            tx_id = send_signed_transaction(body.signed_txn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"On-chain transaction failed: {e}")

    b.status = "disputed"
    db.commit()

    # Notify other party
    other_party = b.worker if current_user == b.creator else b.creator
    notif = Notification(
        recipient=other_party,
        message=f"Bounty {bounty_id} has been placed in DISPUTE by {current_user}. Reason: {body.reason}"
    )
    db.add(notif)
    db.commit()

    broker.publish("bounty.disputed", {
        "bounty_id": bounty_id,
        "initiator": current_user,
        "reason": body.reason,
        "tx_id": tx_id
    })

    return {"bounty_id": bounty_id, "status": "disputed", "tx_id": tx_id}

@router.get("/{bounty_id}/onchain", summary="Poll on-chain status", description="Retrieve the current status of the bounty's escrow application directly from the Algorand blockchain.")
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
