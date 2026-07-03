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
    notifications, events, webhooks, oidc
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
    while True:
        try:
            events = poll_bounty_events(last_round)
            if events:
                # Get a new DB session
                from .database import SessionLocal
                db = SessionLocal()
                try:
                    for event in events:
                        # Map on-chain app status to DB bounty statuses
                        # This is a simplified version of the logic
                        app_id = event.get("app_id")
                        app_status = event.get("app_status") # This might be the program hash or similar

                        # Find the bounty with this app_id
                        from .database import Bounty
                        bounty = db.query(Bounty).filter(Bounty.app_id == app_id).first()
                        if bounty:
                            # Sync logic would go here
                            # For example, if app is closed on-chain, update DB
                            pass
                    if events:
                        last_round = max(e.get("round", 0) for e in events)
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
app.include_router(oidc.router)

# Serve the frontend Dashboard directly under /dashboard
# Check if directory exists
if os.path.exists("dashboard"):
    app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
    print("[SERVER] Mounted /dashboard static files.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
