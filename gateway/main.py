import asyncio
import os
import json
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import init_db, SessionLocal, Bounty, Agent, GitHubPR, Notification
from .auth import get_current_user, generate_challenge, verify_signature, create_jwt_token
from .github import handle_issue_event, handle_pr_event, validate_webhook
from .rate_limiter import RateLimitMiddleware
from .algod_client import (
    get_algod_client, get_default_account,
    NODE_ENV, is_sandbox, compile_escrow_contract,
    get_account_balance, get_asset_holders,
    health_check as algo_health_check,
)
from .middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    CORSAllowlistMiddleware,
)

# Initialize database
init_db()

# CORS origins allowlist – matches deployed frontend + local dev
ALLOWED_ORIGINS: list[str] = [
    "https://algo-bounty-frontend-*.uc.a.run.app",
    "http://localhost:3000",
    "http://localhost:3001",
]

app = FastAPI(title="AlgoBounty Gateway", version="1.0.0")

# ── Middleware (order matters: top to bottom, bottom to top) ──────

# 1. Request size limit (runs first on incoming requests)
app.add_middleware(RequestSizeLimitMiddleware)

# 2. CORS with origin allowlist
app.add_middleware(CORSAllowlistMiddleware, allowed_origins=ALLOWED_ORIGINS)

# 3. Security headers (runs on outgoing responses)
app.add_middleware(SecurityHeadersMiddleware)

# 4. Rate limiting – protects public endpoints from DDoS / spam
app.add_middleware(RateLimitMiddleware)

# Start SSE cleanup background task on app startup
@app.on_event("startup")
async def start_sse_cleanup():
    await broker.start_cleanup()
    print(f"[SSE] Started cleanup task (interval={broker.CLEANUP_INTERVAL_SECONDS}s, stale_timeout={broker.STALE_TIMEOUT_SECONDS}s)")

# SSE Event stream broker
class EventBroker:
    MAX_CONNECTIONS_PER_IP = 10
    STALE_TIMEOUT_SECONDS = 60
    CLEANUP_INTERVAL_SECONDS = 30

    def __init__(self):
        self.listeners: Dict[str, list] = {}  # ip -> [queue, ...]
        self.cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup(self):
        """Start the background cleanup task for stale connections."""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        """Periodically clean up stale entries."""
        while True:
            await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
            await self._cleanup_stale()

    async def _cleanup_stale(self):
        """Remove stale entries where connections have been dead for > 60 seconds."""
        now = time.monotonic()
        stale_ips = []
        for ip, info in list(self.listeners.items()):
            queues = info.get("queues", [])
            registered_at = info.get("registered_at", 0)
            if now - registered_at > self.STALE_TIMEOUT_SECONDS and len(queues) == 0:
                stale_ips.append(ip)
        for ip in stale_ips:
            del self.listeners[ip]

    def get_active_connections(self, ip: str) -> int:
        """Get the number of active connections for an IP."""
        if ip in self.listeners:
            return len(self.listeners[ip].get("queues", []))
        return 0

    def get_total_active_connections(self) -> int:
        """Get total active connections across all IPs."""
        total = 0
        for info in self.listeners.values():
            total += len(info.get("queues", []))
        return total

    async def subscribe(self, ip: str = "unknown"):
        """Subscribe to SSE events with per-IP connection tracking."""
        now = time.monotonic()

        # Initialize tracking for this IP if needed
        if ip not in self.listeners:
            self.listeners[ip] = {"queues": [], "registered_at": now}

        # Check connection limit
        if len(self.listeners[ip]["queues"]) >= self.MAX_CONNECTIONS_PER_IP:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "SSE connection limit reached",
                    "max_connections": self.MAX_CONNECTIONS_PER_IP,
                    "retry_after_seconds": 30
                }
            )

        queue = asyncio.Queue()
        self.listeners[ip]["queues"].append(queue)

        try:
            while True:
                yield await queue.get()
        finally:
            if ip in self.listeners:
                if queue in self.listeners[ip]["queues"]:
                    self.listeners[ip]["queues"].remove(queue)
                if len(self.listeners[ip]["queues"]) == 0:
                    del self.listeners[ip]

    def publish(self, event_type: str, data: dict):
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        for info in self.listeners.values():
            for queue in info.get("queues", []):
                queue.put_nowait(msg)

broker = EventBroker()

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas
class AuthRequest(BaseModel):
    address: str

class AuthVerify(BaseModel):
    address: str
    signature: str
    challenge: str

class BountyCreate(BaseModel):
    description: str
    amount: int
    asset_id: int = 0
    hitm: bool = False
    repo_url: str
    karma_requirement: int = 0
    github_issue: Optional[int] = None
    hitm_review_days: int = 7

# Algorand network config
sandbox_active = is_sandbox()
print(f"[WEB3] Algorand network: {NODE_ENV} (sandbox={sandbox_active})")

# ── Health Check ─────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Public health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": "algobounty-gateway",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": app.version,
        "sandbox_active": sandbox_active,
        "node_env": NODE_ENV,
    }


# ── API Endpoints ────────────────────────────────────────────────

# 1. Authentication
@app.post("/api/v1/auth/request")
def auth_request(body: AuthRequest):
    challenge = generate_challenge(body.address)
    return {
        "challenge": challenge,
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"
    }

@app.post("/api/v1/auth/verify")
def auth_verify(body: AuthVerify, db: Session = Depends(get_db)):
    # Verify the signature
    is_valid = verify_signature(body.address, body.signature, body.challenge)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid wallet signature")

    # Get or create agent
    agent = db.query(Agent).filter(Agent.address == body.address).first()
    if not agent:
        agent = Agent(address=body.address, karma=25)
        db.add(agent)
        db.commit()
        db.refresh(agent)

    # Generate JWT
    token = create_jwt_token(body.address)
    return {
        "jwt": token,
        "address": body.address,
        "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
        "karma": agent.karma
    }

# 2. Bounties Marketplace
@app.get("/api/v1/bounties")
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
        query = query.filter(Bounty.repo_url.contains(repo))
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

@app.get("/api/v1/bounties/{bounty_id}")
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

@app.post("/api/v1/bounties")
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

@app.post("/api/v1/bounties/{bounty_id}/claim")
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

@app.post("/api/v1/bounties/{bounty_id}/submit")
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

@app.post("/api/v1/bounties/{bounty_id}/approve")
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

@app.post("/api/v1/bounties/{bounty_id}/reject")
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

@app.post("/api/v1/bounties/{bounty_id}/dispute")
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


@app.get("/api/v1/bounties/{bounty_id}/onchain")
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


# --- Algorand Network Endpoints ---

@app.get("/api/v1/algorand/health")
def algorand_health():
    """Health check for Algorand network."""
    try:
        status = algo_health_check()
        if status.get("algod") and status.get("indexer"):
            return {"status": "healthy", "network": status["network"], "algod": True, "indexer": True}
        return {"status": "degraded", "network": status["network"], "algod": status.get("algod"), "indexer": status.get("indexer"), "error": status.get("error")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/algorand/balance/{address}")
def algorand_balance(address: str):
    """Return ALGO balance for any address."""
    try:
        return get_account_balance(address)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/algorand/asset/{asset_id}/holders")
def algorand_asset_holders(asset_id: int):
    """Get asset holders for an ASA."""
    try:
        return get_asset_holders(asset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
# 3. Agent profiles
@app.get("/api/v1/agents/{address}")
def get_agent(address: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.address == address).first()
    if not agent:
        # Implicitly register
        agent = Agent(address=address, karma=25)
        db.add(agent)
        db.commit()
        db.refresh(agent)

    return {
        "address": agent.address,
        "karma": agent.karma,
        "completed_bounties": agent.completed_bounties,
        "disputes_lost": agent.disputes_lost
    }

@app.get("/api/v1/agents/me")
def get_my_profile(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return get_agent(current_user, db)

# 4. Notifications
@app.get("/api/v1/notifications")
def list_notifications(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    notifs = db.query(Notification).filter(Notification.recipient == current_user).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": n.id,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat() + "Z"
        } for n in notifs
    ]

@app.post("/api/v1/notifications/{id}/read")
def read_notification(id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == id, Notification.recipient == current_user).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.commit()
    return {"status": "success"}

# 5. Real-time Event Stream (SSE)
@app.get("/api/v1/events")
async def event_stream(request: Request):
    """SSE endpoint for real-time marketplace events. Protected against connection flooding."""
    ip = request.client.host if request.client else "unknown"

    async def event_generator():
        async for event in broker.subscribe(ip):
            yield event

    total_active = broker.get_total_active_connections()
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-SSE-Active-Connections": str(total_active)}
    )

# 6. GitHub webhook endpoint with X-Hub-Signature-256 verification
@app.post("/webhooks/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    GitHub Webhook receiver.
    Verifies HMAC-SHA256 signature via X-Hub-Signature-256 header,
    validates event type, then dispatches.
    """
    # --- Signature verification (MUST be first) ---
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
    client_ip = request.client.host if request.client else "unknown"

    # Read raw body BEFORE calling .json()
    raw_body = await request.body()

    ok, reason = validate_webhook(
        event_type=event_type,
        secret=secret,
        signature=signature,
        delivery_id=delivery_id,
        raw_body=raw_body,
        client_ip=client_ip,
    )
    if not ok:
        return JSONResponse(
            status_code=403,
            content={"status": "rejected", "reason": reason}
        )

    # --- Parse payload ---
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "rejected", "reason": "Invalid JSON payload"}
        )

    # --- Dispatch ---
    if event_type == "issues":
        handle_issue_event(db, payload)
    elif event_type == "pull_request":
        handle_pr_event(db, payload)
    elif event_type == "issue_comment":
        handle_issue_event(db, payload)
    elif event_type == "pull_request_review":
        handle_pr_event(db, payload)

    return {"status": "event_processed"}

# Serve the frontend Dashboard directly under /dashboard
# Check if directory exists
if os.path.exists("dashboard"):
    app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
    print("[SERVER] Mounted /dashboard static files.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
