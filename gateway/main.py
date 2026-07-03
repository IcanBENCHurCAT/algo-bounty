import os
from datetime import datetime, UTC
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .rate_limiter import RateLimitMiddleware
from .algod_client import NODE_ENV, is_sandbox
from .middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    CORSAllowlistMiddleware,
)
from .broker import broker
from .dependencies import get_db
from .indexer import poll_bounty_events, sync_bounty_from_chain
import asyncio
from .routers import (
    auth, bounties, algorand, agents,
    notifications, events, webhooks
)

# Initialize database
init_db()

# CORS origins allowlist – matches deployed frontend + local dev
ALLOWED_ORIGINS: list[str] = [
    "https://algo-bounty-frontend-*.uc.a.run.app",
    "http://localhost:3000",
    "http://localhost:3001",
]

async def indexer_polling_task():
    """Background task to poll Algorand indexer for bounty events."""
    print("[INDEXER] Starting background polling task...")
    last_round = 0
    from .indexer import fetch_app_logs
    import base64

    while True:
        try:
            # Get a new DB session
            from .database import SessionLocal, Bounty, Agent
            db = SessionLocal()
            try:
                # Find all active bounties to poll for logs
                active_bounties = db.query(Bounty).filter(
                    Bounty.status.in_(["open", "claimed", "submitted", "rejected", "disputed"])
                ).all()

                for bounty in active_bounties:
                    if not bounty.app_id:
                        continue

                    logs_list = fetch_app_logs(bounty.app_id, last_round)
                    for log_entry in logs_list:
                        for log_b64 in log_entry["logs"]:
                            log_bytes = base64.b64decode(log_b64)
                            # Handle HITM Auto-Release
                            if log_bytes == b"auto_released_hitm":
                                if bounty.status != "closed":
                                    bounty.status = "closed"
                                    bounty.payout_type = "PAYOUT"
                                    # Karma: +3 worker, +2 creator
                                    worker = db.query(Agent).filter(Agent.address == bounty.worker).first()
                                    if worker: worker.karma += 3
                                    creator = db.query(Agent).filter(Agent.address == bounty.creator).first()
                                    if creator: creator.karma += 2
                                    db.commit()
                                    print(f"[INDEXER] Bounty {bounty.bounty_id} auto-released.")

                            # Handle Dispute Timeout Split
                            elif log_bytes == b"dispute_timeout_split":
                                if bounty.status != "closed":
                                    bounty.status = "closed"
                                    bounty.payout_type = "SPLIT"
                                    # Karma: -1 both parties
                                    worker = db.query(Agent).filter(Agent.address == bounty.worker).first()
                                    if worker: worker.karma -= 1
                                    creator = db.query(Agent).filter(Agent.address == bounty.creator).first()
                                    if creator: creator.karma -= 1
                                    db.commit()
                                    print(f"[INDEXER] Bounty {bounty.bounty_id} dispute timed out (split).")

                            # Handle Claim Expired
                            elif log_bytes == b"claim_expired":
                                if bounty.status != "open":
                                    # Penalty: -20 karma for the ghosting worker
                                    worker = db.query(Agent).filter(Agent.address == bounty.worker).first()
                                    if worker: worker.karma -= 20

                                    bounty.status = "open"
                                    bounty.worker = None
                                    bounty.rejection_count = 0
                                    db.commit()
                                    print(f"[INDEXER] Bounty {bounty.bounty_id} claim expired. Reopened.")

                        if log_entry["round"] > last_round:
                            last_round = log_entry["round"]
            finally:
                db.close()
        except Exception as e:
            print(f"[INDEXER] Polling task error: {e}")

        await asyncio.sleep(10)  # Poll every 10 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start SSE cleanup background task on app startup
    await broker.start_cleanup()
    print(f"[SSE] Started cleanup task (interval={broker.CLEANUP_INTERVAL_SECONDS}s, stale_timeout={broker.STALE_TIMEOUT_SECONDS}s)")

    # Start Indexer polling task
    polling_task = asyncio.create_task(indexer_polling_task())

    yield

    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        print("[INDEXER] Background polling task stopped.")

app = FastAPI(title="AlgoBounty Gateway", version="1.0.0", lifespan=lifespan)

# ── Middleware (order matters: top to bottom, bottom to top) ──────

# 1. Request size limit (runs first on incoming requests)
app.add_middleware(RequestSizeLimitMiddleware)

# 2. CORS with origin allowlist
app.add_middleware(CORSAllowlistMiddleware, allowed_origins=ALLOWED_ORIGINS)

# 3. Security headers (runs on outgoing responses)
app.add_middleware(SecurityHeadersMiddleware)

# 4. Rate limiting – protects public endpoints from DDoS / spam
app.add_middleware(RateLimitMiddleware)

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
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "version": app.version,
        "sandbox_active": sandbox_active,
        "node_env": NODE_ENV,
    }

# ── API Routers ──────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(bounties.router)
app.include_router(algorand.router)
app.include_router(agents.router)
app.include_router(notifications.router)
app.include_router(events.router)
app.include_router(webhooks.router)

# Serve the frontend Dashboard directly under /dashboard
# Check if directory exists
if os.path.exists("dashboard"):
    app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
    print("[SERVER] Mounted /dashboard static files.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
