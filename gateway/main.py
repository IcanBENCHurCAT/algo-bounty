import os
from datetime import datetime, UTC
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .rate_limiter import RateLimitMiddleware
from .algod_client import NODE_ENV, is_sandbox
# from .middleware.x402 import X402Middleware
from .middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    CORSAllowlistMiddleware,
    WebhookApiKeyAuthMiddleware,
    GitHubWebhookSignatureMiddleware,
)
import asyncio
from .broker import broker
from .worker import indexer_worker
from .dependencies import get_db
from .routers import (
    auth, bounties, algorand, agents,
    notifications, events, webhooks, oidc
)

# Initialize database
init_db()

# CORS origins allowlist – matches deployed frontend + local dev + vantage-labs domain
ALLOWED_ORIGINS: list[str] = [
    "https://algo-bounty-frontend-*.us-central1.run.app",
    "https://algo-bounty-frontend-*.uc.a.run.app",
    "https://algo-bounty-frontend-*.a.run.app",
    "https://vantage-labs.com",
    "https://*.vantage-labs.com",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start SSE cleanup background task on app startup
    await broker.start_cleanup()
    print(f"[SSE] Started cleanup task (interval={broker.CLEANUP_INTERVAL_SECONDS}s, stale_timeout={broker.STALE_TIMEOUT_SECONDS}s)")

    # Start indexer polling background task only if explicitly requested or in sandbox mode (local dev)
    run_indexer = os.environ.get("RUN_INDEXER", "true" if NODE_ENV == "sandbox" else "false")
    if run_indexer.lower() == "true":
        asyncio.create_task(indexer_worker())
        print("[INDEXER] Started background indexer polling task")
    else:
        print("[INDEXER] Standalone indexer polling task disabled (running as separate worker)")

    yield

app = FastAPI(title="AlgoBounty Gateway", version="1.0.0", lifespan=lifespan)

# ── Middleware (order matters: top to bottom, bottom to top) ──────

# 1. Request size limit (runs first on incoming requests, innermost base middleware)
app.add_middleware(RequestSizeLimitMiddleware)

# 2. Security headers (runs on outgoing responses)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Webhook API key auth – protects webhook endpoints
app.add_middleware(WebhookApiKeyAuthMiddleware)

# 4.5. x402 Header Protocol Middleware (Disabled for now)
# app.add_middleware(X402Middleware)

# 5. GitHub webhook signature verification
app.add_middleware(GitHubWebhookSignatureMiddleware)

# 5. Rate limiting – protects public endpoints from DDoS / spam
app.add_middleware(RateLimitMiddleware)

# 6. CORS with origin allowlist (MUST BE OUTERMOST so it catches RateLimit/Auth responses)
app.add_middleware(CORSAllowlistMiddleware, allowed_origins=ALLOWED_ORIGINS)

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

# ── Exception Handlers ───────────────────────────────────────────

import traceback
import sys
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions to ensure they are logged and return CORS headers."""
    print(f"[ERROR] Unhandled exception: {exc}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error_type": type(exc).__name__,
            "message": str(exc)
        }
    )

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
