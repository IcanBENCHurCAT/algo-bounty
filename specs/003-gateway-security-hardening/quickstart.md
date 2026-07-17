# Quickstart Validation: Gateway Security Hardening

**Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

---

## Prerequisites

- Python 3.12+ with virtual environment
- Dependencies installed: `pip install -r requirements.txt`
- Environment variables set: `SECRET_KEY`, `ALGORAND_NETWORK=sandbox`

## Validation Scenario 1: Rate Limiter JWT Bypass Fix

### Setup
```bash
export PYTHONPATH=.
export TESTING=False
python gateway/main.py &
```

### Test: Forged Token Is Rate-Limited
```bash
# Send requests with a fake Bearer token — should be rate-limited after threshold
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer aaa.bbb.ccc" \
    http://localhost:8000/api/v1/auth/request
done
# Expected: First 5 return 200/4xx, then 429 responses begin
```

### Test: Valid JWT Bypasses Rate Limit
```bash
# Obtain a real JWT via the auth flow, then:
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer <REAL_JWT>" \
    http://localhost:8000/api/v1/bounties
done
# Expected: All requests return 200 (not 429), even beyond the normal limit
```

### Expected Outcome
- Forged tokens: subject to IP-based rate limiting (429 after threshold)
- Valid tokens: bypass rate limiting as before

---

## Validation Scenario 2: Opaque Error Responses

### Test: Trigger a 500 Error
```bash
# Force an internal error (e.g., by hitting an endpoint with a broken DB state)
# or test via the automated test suite
curl -s http://localhost:8000/api/v1/some-broken-endpoint | python -m json.tool
```

### Expected Response
```json
{
  "detail": "Internal Server Error"
}
```

No `error_type` or `message` fields should be present.

### Verify Server Logs
Check stderr output — the full exception type, message, and traceback should still appear in the server-side logs.

---

## Validation Scenario 3: Contract Compilation (Regression Check)

### Test: Compile Still Works
```bash
# If algokit is installed, trigger contract compilation via the API or directly:
python -c "
from gateway.algod_client import compile_escrow_contract
result = compile_escrow_contract()
print('SUCCESS' if result else 'FAILED')
"
```

### Expected Outcome
- Contract compilation succeeds as before
- No behavioral change from adding explicit `shell=False`

---

## Automated Test Suite

```bash
export PYTHONPATH=.
export TESTING=True
python -m pytest tests/ -v
```

### Expected
- All existing tests pass
- Updated `test_rate_limiter.py` reflects new JWT verification behavior
- No regressions in `test_main_unit.py` or other test modules
