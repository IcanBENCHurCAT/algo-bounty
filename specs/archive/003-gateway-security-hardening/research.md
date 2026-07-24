# Research: Gateway Security Hardening

**Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

---

## R1: JWT Verification in Middleware Context

### Decision
Reuse the existing `verify_jwt_token()` from `gateway/auth.py` inside the rate limiter middleware, but catch all exceptions (including `HTTPException`) to ensure the middleware never crashes. If verification fails for any reason, treat the request as unauthenticated.

### Rationale
- `verify_jwt_token()` already handles HS256 signature validation, expiration checks, and algorithm enforcement via `PyJWT`.
- Importing and calling it directly avoids duplicating cryptographic logic or introducing drift between the auth layer and the rate limiter.
- The function raises `HTTPException` on invalid/expired tokens. In the middleware context we need to **catch** that exception (not propagate it) so the request continues to the normal rate-limiting path rather than returning a 401 from the rate limiter itself.

### Alternatives Considered
| Alternative | Why Rejected |
|---|---|
| Duplicate `jwt.decode()` inline in rate_limiter.py | Violates DRY; risks drift if SECRET_KEY/ALGORITHM changes |
| Use a lightweight `jwt.decode()` without full verification | Defeats the purpose of fixing the vulnerability |
| Add a non-throwing wrapper to `auth.py` | Adds API surface to auth module for a single consumer; catching in middleware is cleaner |

### Key Implementation Detail
The rate limiter must wrap the call in a broad `try/except Exception` because `verify_jwt_token` raises `HTTPException` (which inherits from `Exception`) on failure. The middleware should **never** return a 401 — it simply decides whether to apply IP-based throttling.

---

## R2: Error Response Hardening — OWASP Best Practice

### Decision
Strip `error_type` and `message` fields from the 500 JSONResponse in the global exception handler. Return only `{"detail": "Internal Server Error"}`.

### Rationale
- OWASP Top 10 (A05:2021 – Security Misconfiguration) explicitly flags verbose error messages as a vulnerability.
- `type(exc).__name__` reveals internal class names (e.g., `OperationalError`, `AlgodHTTPError`) that help attackers identify technology stack and specific failure modes.
- `str(exc)` can leak database connection strings, file paths, SQL fragments, or raw blockchain error messages.
- Server-side logging (`print` to stderr + `traceback.print_exc`) is already in place and must be preserved.

### Alternatives Considered
| Alternative | Why Rejected |
|---|---|
| Add a "debug mode" toggle to include error details | Adds complexity; safe default should always be opaque |
| Hash the error and return a correlation ID | Good for production observability but out of scope for this hardening pass |
| Only strip in production (check NODE_ENV) | Risk of misconfiguration; safer to always return opaque responses |

---

## R3: Subprocess `shell=False` — Defense in Depth

### Decision
Add explicit `shell=False` to the `subprocess.run()` call in `compile_escrow_contract()`.

### Rationale
- While `subprocess.run` defaults to `shell=False` when the first argument is a list, being explicit makes the security intent clear to code reviewers and static analysis tools.
- This is a zero-risk change: it simply makes the existing default behavior explicit.
- Prevents future regressions if someone refactors the call to use a string command.

### Alternatives Considered
| Alternative | Why Rejected |
|---|---|
| Do nothing (default is already safe) | Explicit is better than implicit for security-critical code |
| Add input validation on contract_path | Path is already hardcoded from `__file__`; validation would be defense-in-depth on top of defense-in-depth |

---

## R4: Existing Test Impact Analysis

### Finding: `test_rate_limiter.py` Line 75 Will Need Updating
The existing test `test_rate_limiter_middleware_bypass` explicitly tests that `Bearer aaa.bbb.ccc` bypasses rate limiting:
```python
res = client.get("/api/v1/test-limiter", headers={"Authorization": "Bearer aaa.bbb.ccc"})
assert res.status_code == 200
```

This test currently **passes** because the regex check accepts the fake token. After the fix, this test must be **updated** to:
1. Expect the fake token to be rate-limited (not bypassed)
2. Add a new test using a real JWT (generated via `create_jwt_token`) to verify legitimate bypass still works

### Finding: `conftest.py` Sets `TESTING="True"`
The `conftest.py` sets `TESTING="True"` globally, which bypasses rate limiting entirely. The rate limiter unit tests manage their own `TESTING` env var patching. No conflict expected.

### Finding: `test_main_unit.py` — Likely Not Affected
The global exception handler test (if any) would need to be checked, but `test_main_unit.py` is only 323 bytes — likely minimal. The handler change is a field removal, so any test asserting on `error_type` or `message` fields would need updating.
