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

import os
import re
import secrets
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
    "https://algo-bounty-frontend-*.us-central1.run.app",
    "https://algo-bounty-frontend-*.uc.a.run.app",
    "https://algo-bounty-frontend-*.a.run.app",
    "http://localhost:3000",
    "http://localhost:3001",
]


from starlette.middleware.cors import CORSMiddleware
from typing import cast
import typing

class CORSAllowlistMiddleware(CORSMiddleware):
    """Enforce an allowlist of allowed CORS origins using Starlette's CORSMiddleware.

    Accepts the allowlist as a keyword argument when constructing
    the middleware instance.
    """

    def __init__(self, app, allowed_origins: list[str] | None = None):
        origins = allowed_origins or _DEFAULT_ALLOWED_ORIGINS

        # Convert wildcard patterns to regexes and combine them
        regex_parts = []
        for pattern in origins:
            # Escape regex special characters, then restore wildcards as .*
            regex_pattern = re.escape(pattern).replace(r"\*", ".*")
            # Ensure exact match by anchoring
            regex_parts.append(f"^{regex_pattern}$")
        
        combined_regex = "|".join(regex_parts)

        # Starlette's CORSMiddleware natively supports allow_origin_regex (as a string)
        super().__init__(
            app=app,
            allow_origins=[],
            allow_origin_regex=combined_regex,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )


# ── Webhook API key authentication ──────────────────────────────

class WebhookApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Enforce X-API-Key header on webhook endpoints.

    Validates that requests to webhook paths include a valid API key
    configured via WEBHOOK_API_KEY environment variable.
    Skips validation for non-webhook paths.
    """

    def __init__(self, app, api_key: str | None = None):
        super().__init__(app)
        self.required_key = api_key or os.environ.get(
            "WEBHOOK_API_KEY", ""
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Only enforce on webhook paths
        if "/webhooks" not in path:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")

        # Allow requests without API key if no key is configured
        # (development mode)
        if not self.required_key:
            return await call_next(request)

        # Validate API key
        if not secrets.compare_digest(api_key, self.required_key):
            return Response(
                content='{"error": "Missing or invalid X-API-Key header"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)


# ── GitHub Webhook Signature Verification ──────────────────────

class GitHubWebhookSignatureMiddleware(BaseHTTPMiddleware):
    """Verify GitHub webhook signature for requests to /webhooks/github."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path != "/webhooks/github":
            return await call_next(request)

        # 1. Verification is only required if GITHUB_WEBHOOK_SECRET is set
        from gateway.config import settings
        from gateway.github import verify_webhook_signature
        import json

        secret = settings.GITHUB_WEBHOOK_SECRET
        signature = request.headers.get("X-Hub-Signature-256", "")

        # Read raw body
        body_bytes = await request.body()

        # 2. Verify signature
        if secret:
            if not verify_webhook_signature(body_bytes, signature, secret):
                return Response(
                    content='{"status": "rejected", "reason": "Invalid signature"}',
                    status_code=403,
                    media_type="application/json",
                )

        # 3. Store body and parsed payload in request state for downstream use
        request.state.github_body = body_bytes
        try:
            request.state.github_payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return Response(
                content='{"status": "rejected", "reason": "Invalid JSON payload"}',
                status_code=400,
                media_type="application/json",
            )

        # 4. We need to override the request.body() method so that the router can read it again if needed,
        # but since we're using request.state, we can just update the router to use request.state.
        # Alternatively, we can use a custom Request subclass or wrap the call.
        # For FastAPI, the simplest is often request.state.

        return await call_next(request)
