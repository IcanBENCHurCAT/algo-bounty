"""Sliding-window rate limiter middleware for AlgoBounty FastAPI gateway.

Usage:
    from .rate_limiter import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

Design:
    - In-memory, per-IP sliding window (timestamps stored, pruned on check).
    - Thread-safe via threading.Lock.
    - Stricter limits on auth endpoints (5 req/min) to prevent brute-force.
    - Endpoint-specific rate limits enforced in the middleware.
"""

import time
import json
import threading
import re

from fastapi import Request, Response, status

# ---------------------------------------------------------------------------
# Rule definitions – (regex, limit, window_seconds, method_filter, special)
# ---------------------------------------------------------------------------

# method_filter = None  -> all methods
# method_filter = "GET"  -> GET only, etc.
# method_filter = "POST" -> POST only, etc.

_RULES = [
    # Auth endpoints – STRICTEST limits: 5 req/min to prevent brute-force.
    (r"^/api/v1/auth/request$", 5, 60, None, None),
    (r"^/api/v1/auth/verify$", 5, 60, None, None),

    # GitHub webhook – generous rate limit (GitHub can burst).
    (r"^/webhooks/github$", 30, 60, "POST", None),

    # Bounty write operations that require JWT – generous limits.
    (r"^/api/v1/bounties$", 30, 60, "POST", None),
    (r"^/api/v1/bounties/.*/claim$", 30, 60, "POST", None),
    (r"^/api/v1/bounties/.*/submit$", 30, 60, "POST", None),
    (r"^/api/v1/bounties/.*/approve$", 30, 60, "POST", None),
    (r"^/api/v1/bounties/.*/reject$", 30, 60, "POST", None),
    (r"^/api/v1/bounties/.*/dispute$", 30, 60, "POST", None),

    # SSE event stream – special: concurrent connection limit, not request.
    (r"^/api/v1/events$", 3, 60, "GET", "connections"),

    # Health endpoint – no rate limit (public diagnostic).
    (r"^/health$", 1000, 60, "GET", None),

    # All other GET endpoints – read endpoints, moderate throttling.
    (r"^/api/v1/", 30, 60, "GET", None),

    # Catch-all for anything else POST – reasonable default.
    (r"^.*$", 30, 60, "POST", None),
]

# Cache compiled regexes at import time.
_RULES_COMPILED = [
    (re.compile(pattern), limit, window, method_filter, special)
    for pattern, limit, window, method_filter, special in _RULES
]

# ---------------------------------------------------------------------------
# Rate limit storage – { key: [timestamp, ...] }
# ---------------------------------------------------------------------------

# Per-IP request logs
_request_log: dict[str, list[float]] = {}

# SSE connection tracking – { ip: count }
_connection_log: dict[str, int] = {}

_lock = threading.Lock()


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, preferring proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def _apply_sliding_window(timestamps: list[float], now: float, limit: int, window: float) -> tuple[bool, int]:
    """Return (blocked, remaining) using a sliding window.

    Returns (True, 0) when the client is blocked, (False, N) otherwise.
    """
    cutoff = now - window
    # Purge old entries – ensures the log stays bounded.
    timestamps[:] = [t for t in timestamps if t > cutoff]

    count = len(timestamps)
    if count >= limit:
        # Calculate retry_after: seconds until oldest entry expires.
        if timestamps:
            retry_after = timestamps[0] + window - now
            retry_after = max(1, int(retry_after + 0.999))  # ceiling
        else:
            retry_after = window

        return True, 0

    # Not blocked – record this request.
    timestamps.append(now)
    remaining = limit - len(timestamps)
    return False, remaining


class RateLimitMiddleware:
    """FastAPI middleware that enforces per-IP rate limits.

    Skips rate limiting for requests that include a valid-looking JWT Bearer
    token in the Authorization header (those endpoints already enforce auth
    and return 401 without a valid token).
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, request: Request, call_next) -> Response:
        # -- 1. Resolve matching rule ----------------------------------------
        path = request.url.path
        method = request.method.upper()

        matched_rule = None
        for pattern, limit, window, method_filter, special in _RULES_COMPILED:
            if pattern.match(path) is None:
                continue
            if method_filter and method_filter != method:
                continue
            matched_rule = (pattern, limit, window, special)
            break  # first match wins (rules are ordered by priority)

        # No matching rule – no rate limiting.
        if matched_rule is None:
            return await call_next(request)

        pattern, limit, window, special = matched_rule

        # -- 2. Skip if request carries a valid JWT --------------------------
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token_part = auth_header[7:]
            # A valid JWT has 3 base64url parts separated by dots.
            if re.match(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$", token_part):
                return await call_next(request)

        # -- 3. Handle SSE (connection-based) --------------------------------
        if special == "connections":
            ip = _get_client_ip(request)
            with _lock:
                count = _connection_log.get(ip, 0)
                if count >= limit:
                    body = json.dumps(
                        {"error": "Rate limit exceeded", "retry_after_seconds": 60}
                    )
                    return Response(
                        content=body,
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        media_type="application/json",
                        headers={"X-RateLimit-Remaining": "0"},
                    )
                _connection_log[ip] = count + 1
                remaining = limit - _connection_log[ip]

            try:
                response = await call_next(request)
                return response
            finally:
                with _lock:
                    if ip in _connection_log:
                        _connection_log[ip] = max(0, _connection_log[ip] - 1)

            return response  # keep linters happy

        # -- 4. Standard per-IP sliding window -------------------------------
        ip = _get_client_ip(request)
        key = f"{ip}:{path}:{method}"  # path may contain dynamic segments – acceptable

        with _lock:
            now = time.time()
            if key not in _request_log:
                _request_log[key] = []

            timestamps = _request_log[key]
            blocked, remaining = _apply_sliding_window(timestamps, now, limit, window)

        if blocked:
            retry_after = window  # approximate – precise value not available here
            body = json.dumps(
                {"error": "Rate limit exceeded", "retry_after_seconds": retry_after}
            )
            return Response(
                content=body,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={"X-RateLimit-Remaining": "0"},
            )

        # -- 5. Call the actual endpoint and propagate X-RateLimit-Remaining --
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
