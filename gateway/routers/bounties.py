import re
from datetime import datetime, UTC
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from ..database import Bounty, Agent, GitHubPR, Notification
from ..auth import get_current_user
from ..config import settings
from ..dependencies import get_db
from ..github import post_github_comment_and_labels, extract_bounty_ids
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

from pydantic import BaseModel
class TxnGenResponse(BaseModel):
    unsigned_txn: str

@router.get("", summary="List all bounties", description="Retrieve a list of bounties with optional filtering by status, repository, amount, karma requirement, and HITM mode.")
def list_bounties(
    status: Optional[str] = None,
    repo: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    min_karma: Optional[int] = None,
    hitm: Optional[bool] = None,
    creator: Optional[str] = None,
    worker: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Bounty)
    if creator:
        query = query.filter(Bounty.creator == creator)
    if worker:
        query = query.filter(Bounty.worker == worker)
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

            # Compile the escrow contract (approval and clear program)
            approval_teal = compile_escrow_contract("approval")
            clear_teal = compile_escrow_contract("clear")
            
            import base64
            compile_resp_app = client.compile(approval_teal)
            approval_compiled = base64.b64decode(compile_resp_app.get("result", ""))

            compile_resp_clr = client.compile(clear_teal)
            clear_compiled = base64.b64decode(compile_resp_clr.get("result", ""))

            if approval_compiled and clear_compiled:
                params = client.suggested_params()

                # Encode app args
                from algosdk.abi import ABIType
                bounty_id_bytes = body.description[:64].encode()
                escrow_amount = int(body.amount)
                asset_id = int(body.asset_id)
                is_hitm = 1 if body.hitm else 0
                review_days = int(body.hitm_review_days)

                platform_account = get_default_account()
                if platform_account is None:
                    raise HTTPException(
                        status_code=500,
                        detail="PLATFORM_PRIVATE_KEY not configured"
                    )

                # Mediator is the platform account (default)
                mediator_address = platform_account.address
                # Treasury is configured in config.py
                treasury_address = settings.TREASURY_ADDRESS or platform_account.address

                from algosdk.abi import Method
                deploy_method = Method.from_signature("deploy()void")
                deploy_selector = deploy_method.get_selector()

                from algosdk.transaction import ApplicationCreateTxn, OnComplete, StateSchema
                create_txn = ApplicationCreateTxn(
                    sender=platform_account.address,
                    sp=params,
                    on_complete=OnComplete.NoOpOC,
                    approval_program=approval_compiled,
                    clear_program=clear_compiled,
                    global_schema=StateSchema(0, 0),
                    local_schema=StateSchema(0, 0),
                    app_args=[deploy_selector],
                    extra_pages=2,
                )

                signed_txn = create_txn.sign(platform_account.private_key)
                tx_id = client.send_transaction(signed_txn)

                # Wait for confirmation
                from algosdk.transaction import wait_for_confirmation
                pending_info = wait_for_confirmation(client, tx_id, 4)
                if pending_info:
                    app_id = pending_info.get("application-index")
                    onchain = app_id is not None and app_id > 0

                    if onchain:
                        from algosdk.logic import get_application_address
                        app_address = get_application_address(app_id)

                        # Step 2: Fund the contract address (escrow amount + 0.35 ALGO for box MBR)
                        mbr_buffer = 350_000
                        fund_amount = escrow_amount + mbr_buffer

                        from algosdk.transaction import PaymentTxn
                        fund_txn = PaymentTxn(
                            sender=platform_account.address,
                            sp=params,
                            receiver=app_address,
                            amt=fund_amount
                        )
                        signed_fund = fund_txn.sign(platform_account.private_key)
                        fund_txid = client.send_transaction(signed_fund)
                        wait_for_confirmation(client, fund_txid, 4)

                        # Step 3: Call create_bounty NoOp to initialize contract state
                        method = Method.from_signature("create_bounty(byte[],uint64,uint64,uint64,uint64,address,address)void")
                        selector = method.get_selector()

                        import algosdk.encoding as encoding
                        bounty_id_arg = ABIType.from_string("byte[]").encode(bounty_id_bytes)
                        escrow_amount_arg = ABIType.from_string("uint64").encode(escrow_amount)
                        is_hitm_arg = ABIType.from_string("uint64").encode(is_hitm)
                        asset_id_arg = ABIType.from_string("uint64").encode(asset_id)
                        review_days_arg = ABIType.from_string("uint64").encode(review_days)
                        mediator_arg = encoding.decode_address(mediator_address)
                        treasury_arg = encoding.decode_address(treasury_address)

                        app_args = [
                            selector,
                            bounty_id_arg,
                            escrow_amount_arg,
                            is_hitm_arg,
                            asset_id_arg,
                            review_days_arg,
                            mediator_arg,
                            treasury_arg
                        ]

                        from algosdk.transaction import ApplicationNoOpTxn, calculate_group_id
                        box_names1 = [
                            b"state", b"mediator_address", b"treasury_address",
                            b"escrow_amount", b"bounty_id", b"creator_address",
                            b"asset_id"
                        ]
                        boxes1 = [(app_id, name) for name in box_names1]

                        box_names2 = [
                            b"is_hitm", b"review_days", b"github_status"
                        ]
                        boxes2 = [(app_id, name) for name in box_names2]

                        call_txn1 = ApplicationNoOpTxn(
                            sender=platform_account.address,
                            sp=params,
                            index=app_id,
                            app_args=app_args,
                            boxes=boxes1
                        )

                        status_method = Method.from_signature("set_github_status(byte[])void")
                        encoded_pending = status_method.args[0].type.encode(b"pending")
                        call_txn2 = ApplicationNoOpTxn(
                            sender=platform_account.address,
                            sp=params,
                            index=app_id,
                            app_args=[status_method.get_selector(), encoded_pending],
                            boxes=boxes2
                        )

                        # Group transactions to pool the box references budget
                        gid = calculate_group_id([call_txn1, call_txn2])
                        call_txn1.group = gid
                        call_txn2.group = gid

                        signed1 = call_txn1.sign(platform_account.private_key)
                        signed2 = call_txn2.sign(platform_account.private_key)

                        call_txid = client.send_transactions([signed1, signed2])
                        wait_for_confirmation(client, call_txid, 4)

        except Exception as e:
            print(f"[WEB3] Escrow deploy failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to deploy escrow smart contract on-chain: {e}"
            )

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

@router.post("/{bounty_id}/claim/txn", response_model=TxnGenResponse, summary="Generate unsigned claim transaction")
async def get_claim_txn(
    bounty_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.app_id is None:
        raise HTTPException(status_code=400, detail="Bounty has no deployed smart contract application ID.")
    if b.status != "open":
        raise HTTPException(status_code=400, detail="Bounty not claimable")
    if b.creator == current_user:
        raise HTTPException(status_code=400, detail="Cannot claim your own bounty")

    # Check worker karma requirement
    worker = db.query(Agent).filter(Agent.address == current_user).first()
    if not worker or worker.karma < b.karma_requirement:
        raise HTTPException(status_code=403, detail=f"Insufficient karma. Required: {b.karma_requirement}")

    client = get_algod_client()
    params = client.suggested_params()
    params.fee = 1000
    params.flat_fee = True

    from algosdk.abi import Method
    claim_method = Method.from_signature("claim_bounty()void")
    claim_selector = claim_method.get_selector()

    from algosdk.transaction import ApplicationNoOpTxn
    claim_boxes = [
        (b.app_id, b"state"), (b.app_id, b"agent_address"), (b.app_id, b"asset_id"),
        (b.app_id, b"creator_address"), (b.app_id, b"claim_deadline"), (b.app_id, b"claim_timestamp")
    ]

    claim_txn = ApplicationNoOpTxn(
        sender=current_user,
        sp=params,
        index=b.app_id,
        app_args=[claim_selector],
        boxes=claim_boxes
    )
    
    import algosdk.encoding as encoding
    txn_b64 = encoding.msgpack_encode(claim_txn)
    
    return {"unsigned_txn": txn_b64}

@router.post("/{bounty_id}/claim", summary="Claim a bounty", description="Allows a worker to claim an open bounty. Validates karma requirements and processes on-chain claim if a signed transaction is provided.")
async def claim_bounty(
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
    if settings.ALGORAND_NETWORK != "sandbox" and not body.signed_txn:
        raise HTTPException(status_code=400, detail="signed_txn is required")

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

    # GitHub Update
    repo_url, issue_num = _get_bounty_github_info(b)
    if repo_url and issue_num:
        comment_text = (
            f"🤝 **Bounty Claimed!**\n\n"
            f"Agent `{current_user}` has claimed this bounty on the AlgoBounty Dashboard.\n"
            f"The bounty status has transitioned to **CLAIMED**."
        )
        await post_github_comment_and_labels(
            repo_url, issue_num,
            comment=comment_text,
            add_labels=["bounty:claimed"]
        )

    return {"bounty_id": bounty_id, "status": "claimed", "worker": current_user, "tx_id": tx_id}

@router.post("/{bounty_id}/submit", summary="Submit work for a bounty", description="Allows the claiming worker to submit their solution (PR URL). Updates bounty status to 'submitted'.")
async def submit_work(
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
    if settings.ALGORAND_NETWORK != "sandbox" and not body.signed_txn:
        raise HTTPException(status_code=400, detail="signed_txn is required")

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

    # GitHub Update
    repo_url, issue_num = _get_bounty_github_info(b)
    if repo_url and issue_num:
        comment_text = (
            f"🚀 **Solution Submitted!**\n\n"
            f"Agent `{current_user}` has submitted their work: {body.pr_url}\n"
            f"The bounty status is now **SUBMITTED**."
        )
        await post_github_comment_and_labels(
            repo_url, issue_num,
            comment=comment_text,
            add_labels=["bounty:submitted"],
            remove_labels=["bounty:claimed"]
        )

    return {"bounty_id": bounty_id, "status": "submitted", "tx_id": tx_id}

@router.post("/{bounty_id}/approve/txn", response_model=TxnGenResponse, summary="Generate unsigned approve transaction")
async def get_approve_txn(
    bounty_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bounty not found")
    if b.app_id is None:
        raise HTTPException(status_code=400, detail="Bounty has no deployed smart contract application ID.")
    if b.creator != current_user:
        raise HTTPException(status_code=403, detail="Only creator can approve work")
    if b.status != "submitted":
        raise HTTPException(status_code=400, detail="Bounty has no work submitted to approve")

    client = get_algod_client()
    params = client.suggested_params()
    params.fee = 3000  # 2 inner payment transfers + 1 outer call = 3 fees
    params.flat_fee = True

    from algosdk.abi import Method
    approve_method = Method.from_signature("approve_work()void")
    approve_selector = approve_method.get_selector()

    from algosdk.transaction import ApplicationNoOpTxn
    approve_boxes = [
        (b.app_id, b"state"),
        (b.app_id, b"escrow_amount"),
        (b.app_id, b"asset_id"),
        (b.app_id, b"payout_type"),
        (b.app_id, b"treasury_address"),
        (b.app_id, b"agent_address"),
        (b.app_id, b"creator_address")
    ]

    approve_txn = ApplicationNoOpTxn(
        sender=current_user,
        sp=params,
        index=b.app_id,
        app_args=[approve_selector],
        boxes=approve_boxes,
        accounts=[b.worker]
    )
    
    import algosdk.encoding as encoding
    txn_b64 = encoding.msgpack_encode(approve_txn)
    
    return {"unsigned_txn": txn_b64}

@router.post("/{bounty_id}/approve", summary="Approve submitted work", description="Allows the creator to approve the submitted work, closing the bounty and releasing funds. Awards +10 karma to worker and +5 to creator.")
async def approve_work(
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
    if settings.ALGORAND_NETWORK != "sandbox" and not body.signed_txn:
        raise HTTPException(status_code=400, detail="signed_txn is required")

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

    # GitHub Update
    repo_url, issue_num = _get_bounty_github_info(b)
    if repo_url and issue_num:
        comment_text = (
            f"🎉 **Bounty Completed & Funds Released!**\n\n"
            f"Creator `{current_user}` has approved the work. "
            f"The escrow has been closed and funds released to `{b.worker}`."
        )
        await post_github_comment_and_labels(
            repo_url, issue_num,
            comment=comment_text,
            add_labels=["bounty:completed"],
            remove_labels=["bounty:submitted", "bounty:claimed"]
        )

    return {"bounty_id": bounty_id, "status": "closed", "payout_type": "PAYOUT", "tx_id": tx_id}

@router.post("/{bounty_id}/reject", summary="Reject submitted work", description="Allows the creator to reject submitted work. Increments rejection count and applies progressive karma penalties to the worker.")
async def reject_work(
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

    # GitHub Update
    repo_url, issue_num = _get_bounty_github_info(b)
    if repo_url and issue_num:
        comment_text = (
            f"❌ **Solution Rejected**\n\n"
            f"Creator `{current_user}` has rejected the submitted solution.\n"
            f"**Reason**: {body.reason}\n"
            f"Bounty status: **REJECTED** (Worker can resubmit)."
        )
        await post_github_comment_and_labels(
            repo_url, issue_num,
            comment=comment_text,
            remove_labels=["bounty:submitted"]
        )

    return {"bounty_id": bounty_id, "status": "rejected", "rejection_count": b.rejection_count, "tx_id": tx_id}

@router.post("/{bounty_id}/dispute", summary="Open a dispute", description="Allows either the creator or the worker to open a dispute if the work is in submitted or rejected state.")
async def dispute_work(
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

    # GitHub Update
    repo_url, issue_num = _get_bounty_github_info(b)
    if repo_url and issue_num:
        comment_text = (
            f"⚠️ **Dispute Opened**\n\n"
            f"Participant `{current_user}` has opened a dispute.\n"
            f"**Reason**: {body.reason}\n"
            f"Bounty status: **DISPUTED**."
        )
        await post_github_comment_and_labels(
            repo_url, issue_num,
            comment=comment_text,
            add_labels=["bounty:disputed"]
        )

    return {"bounty_id": bounty_id, "status": "disputed", "tx_id": tx_id}

def _get_bounty_github_info(bounty: Bounty) -> tuple[Optional[str], Optional[int]]:
    """Helper to extract GitHub owner/repo and issue number from bounty."""
    if not bounty.repo_url:
        return None, None

    # Try to extract issue number from bounty_id (b_123)
    issue_num = None
    if bounty.bounty_id.startswith("b_"):
        try:
            issue_num = int(bounty.bounty_id[2:])
        except ValueError:
            pass

    return bounty.repo_url, issue_num

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
