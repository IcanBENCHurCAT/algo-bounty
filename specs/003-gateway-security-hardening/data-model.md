# Data Model: Gateway Security Hardening

**Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

---

## Summary

This feature introduces **no new data entities, tables, or schemas**. All changes are behavioral modifications to existing middleware and exception handling code.

## Affected Components

### Rate Limiter Middleware (`gateway/rate_limiter.py`)

**Current behavior**: JWT check is format-only (regex `^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$`).

**New behavior**: JWT check performs cryptographic verification via `verify_jwt_token()` from `gateway/auth.py`.

| Aspect | Before | After |
|---|---|---|
| JWT validation | Regex format check | Full HS256 signature + expiry verification |
| Invalid JWT handling | Bypass rate limit (treated as authenticated) | Fall through to IP-based rate limiting |
| Verification failure | N/A (regex never throws) | Silently caught, request treated as unauthenticated |
| New import | None | `gateway.auth.verify_jwt_token` |

### Global Exception Handler (`gateway/main.py`)

**Current response body** (500):
```json
{
  "detail": "Internal Server Error",
  "error_type": "SomeException",
  "message": "detailed error info..."
}
```

**New response body** (500):
```json
{
  "detail": "Internal Server Error"
}
```

| Aspect | Before | After |
|---|---|---|
| `detail` field | Present | Present (unchanged) |
| `error_type` field | Present (leaks class name) | **Removed** |
| `message` field | Present (leaks `str(exc)`) | **Removed** |
| Server-side logging | Full traceback to stderr | Unchanged |

### Contract Compilation (`gateway/algod_client.py`)

**Current**: `subprocess.run([...], capture_output=True, text=True, timeout=30)`

**New**: `subprocess.run([...], capture_output=True, text=True, timeout=30, shell=False)`

No functional change — makes security intent explicit.

## State Transitions

N/A — This feature does not modify any state machines, database schemas, or contract states.
