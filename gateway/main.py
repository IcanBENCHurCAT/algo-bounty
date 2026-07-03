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
    WebhookApiKeyAuthMiddleware,
)
from .broker import broker
from .dependencies import get_db
from .routers import (
    auth, bounties, algorand, agents,
    notifications, events, webhooks, oidc
)

# Initialize database
init_db()

# CORS origins allowlist – matches deployed frontend + local dev
# NO wildcard (*) origins allowed — specific domains only
ALLOWED_ORIGINS: list[str] = [
    "https://aljobounty.com",
    "https://www.aljobounty.com",
    "https://algo-bounty-frontend-*.uc.a.run.app",
    "https://vantage-labs.com",
    "https://*.vantage-labs.com",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start SSE cleanup background task on app startup
    await broker.start_cleanup()
    print(f"[SSE] Started cleanup task (interval={broker.CLEANUP_INTERVAL_SECONDS}s, stale_timeout={broker.STALE_TIMEOUT_SECONDS}s)")

    yield

app = FastAPI(title="AlgoBounty Gateway", version="1.0.0", lifespan=lifespan)

# ── Middleware (order matters: top to bottom, bottom to top) ──────

# 1. Request size limit (runs first on incoming requests)
app.add_middleware(RequestSizeLimitMiddleware)

# 2. CORS with origin allowlist
app.add_middleware(CORSAllowlistMiddleware, allowed_origins=ALLOWED_ORIGINS)

# 3. Security headers (runs on outgoing responses)
app.add_middleware(SecurityHeadersMiddleware)

# 4. Webhook API key auth – protects webhook endpoints
app.add_middleware(WebhookApiKeyAuthMiddleware)

# 5. Rate limiting – protects public endpoints from DDoS / spam
app.add_middleware(RateLimitMiddleware)

# Algorand network config
sandbox_active = is_sandbox()
print(f"[WEB3] Algorand network: {NODE_ENV} (sandbox={sandbox_active})")

# ── Health Check ─────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Public health check endpoint for load balancers and monitoring.

    Returns service status, database connectivity, and version info.
    Never crashes even if the database is down — reports status as disconnected.
    """
    db_status = "disconnected"
    try:
        from ..dependencies import get_db
        # Quick DB connectivity test
        from ..database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "db": db_status,
        "version": app.version,
        "service": "algobounty-gateway",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
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
