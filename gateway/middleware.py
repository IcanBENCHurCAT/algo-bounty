"""
Security middleware for AlgoBounty FastAPI gateway.

Provides:
  - Security headers (CSP, HSTS, X-Frame-Options, etc.)
  - Request size limiting (1 MB default)
  - CORS with configurable origin allowlist

Usage:
    from .middleware import SecurityMiddleware
    app.add_middleware(SecurityMiddleware, allowed_origins=[...])
"""

import re
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# ── Default security headers ─────────────────────────────────────
_DEFAULT_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' https://mtivcwposaunlsiefwre.supabase.co;"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _DEFAULT_HEADERS.items():
            response.headers[header] = value
        return response


# ── Request size limit ───────────────────────────────────────────
_REQUEST_SIZE_LIMIT = 1 * 1024 * 1024  # 1 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds the configured size limit."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > _REQUEST_SIZE_LIMIT:
                    return Response(
                        content='{"error": "Request body too large"}',
                        status_code=413,
                        media_type="application/json",
                    )
            except ValueError:
                pass
        return await call_next(request)


# ── CORS with origin allowlist ───────────────────────────────────

# Default allowed origins – update when deploying to production
_DEFAULT_ALLOWED_ORIGINS: list[str] = [
    "https://algo-bounty-frontend-*.uc.a.run.app",
    "http://localhost:3000",
    "http://localhost:3001",
]


class CORSAllowlistMiddleware(BaseHTTPMiddleware):
    """Enforce an allowlist of allowed CORS origins.

    Falls back to the default if no custom origins are provided.
    Accepts the allowlist as a keyword argument when constructing
    the middleware instance (see FastAPI docs for passing kwargs to
    middleware classes).
    """

    allowed_origins: list[str]

    def __init__(self, app, allowed_origins: list[str] | None = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or _DEFAULT_ALLOWED_ORIGINS

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin", "")

        # Simple CORS: check if the origin is in our allowlist
        if origin and self._origin_matches(origin):
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, X-Requested-With, "
                "X-Hub-Signature-256, X-GitHub-Event, X-GitHub-Delivery"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # No origin header (simple requests like HTML form POSTs) – let it through
        return await call_next(request)

    def _origin_matches(self, origin: str) -> bool:
        """Check if an origin matches the allowlist, including wildcard patterns."""
        for pattern in self.allowed_origins:
            # Convert wildcard pattern to regex
            regex_pattern = re.escape(pattern).replace(r"\*", ".*")
            if re.match(f"^{regex_pattern}$", origin, re.IGNORECASE):
                return True
        return False
