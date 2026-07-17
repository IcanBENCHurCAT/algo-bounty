# API Contract Changes: Gateway Security Hardening

**Date**: 2026-07-16 | **Spec**: [spec.md](../spec.md)

---

## Breaking Change: 500 Error Response Body

### Before (current)

```
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "detail": "Internal Server Error",
  "error_type": "<exception class name>",
  "message": "<str(exc)>"
}
```

### After (hardened)

```
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "detail": "Internal Server Error"
}
```

### Impact Assessment

- **Dashboard (frontend)**: Should already handle 500s generically. If any code reads `error_type` or `message` from 500 responses, it will get `undefined`. Low risk — frontend typically shows a generic error toast on 500.
- **External consumers**: Any client parsing `error_type` or `message` from 500 responses will need to be updated. This is considered a **security improvement**, not a regression.
- **Monitoring/alerting**: Systems that parse response bodies for 500 classification should switch to server-side log parsing.

---

## Non-Breaking Change: Rate Limiter Behavior

### Before (current)

Any request with `Authorization: Bearer <3-segment-base64url-string>` bypasses IP-based rate limiting, regardless of whether the JWT is valid.

### After (hardened)

Only requests with a **cryptographically valid, non-expired JWT** bypass IP-based rate limiting. Invalid/expired/forged tokens are treated as unauthenticated.

### Impact Assessment

- **Legitimate users**: Zero impact. Valid JWTs continue to bypass rate limiting.
- **Automated clients with expired tokens**: Will now be subject to rate limiting. This is correct behavior.
- **Attackers**: Can no longer bypass rate limits with trivial fake tokens.
