# Implementation Plan: Gateway Security Hardening

**Branch**: `003-gateway-security-hardening` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-gateway-security-hardening/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A security audit revealed three vulnerabilities in the AlgoBounty gateway. The most critical is a rate-limiter bypass where any request with a fake JWT-formatted `Authorization` header completely bypasses IP-based rate limiting. This plan fixes the bypass by performing real JWT signature verification in the middleware, removes information leakage from the global 500 error response, and adds explicit `shell=False` to a subprocess call as defense-in-depth.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, Starlette, PyJWT, SQLAlchemy, py-algorand-sdk

**Storage**: PostgreSQL (production via asyncpg) / SQLite (local dev)

**Testing**: pytest, pytest-asyncio, unittest.mock

**Target Platform**: Linux server (GCP Cloud Run)

**Project Type**: Web service (FastAPI gateway)

**Performance Goals**: No degradation from adding JWT decode to the rate limiter hot path. PyJWT HS256 decode is <1ms per call.

**Constraints**: The rate limiter middleware must never return 401 or crash — it only decides whether to apply IP-based throttling.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [N/A] **Smart Contract Language**: No contract changes in this feature.
- [N/A] **RekeyTo Protection**: No contract changes in this feature.
- [N/A] **Box Storage Limits**: No contract changes in this feature.
- [N/A] **Karma Ledger Gatekeeping**: No bounty creation/claiming changes.
- [N/A] **Escrow Funding Verification**: No escrow changes.
- [N/A] **Atomic Payout Group**: No payout changes.
- [N/A] **OIDC Security**: No OIDC changes. Note: the rate limiter fix aligns with the constitution's security posture.
- [N/A] **Database Compatibility**: No database changes.
- [N/A] **Continuous Worker Setup**: No worker changes.

**Gate Result**: ✅ PASS — This feature is a gateway-only security hardening with no smart contract, database, or worker changes. All constitution principles are unaffected.

## Project Structure

### Documentation (this feature)

```text
specs/003-gateway-security-hardening/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Research decisions
├── data-model.md        # Phase 1: Behavioral change mapping
├── quickstart.md        # Phase 1: Validation scenarios
├── contracts/
│   └── api-changes.md   # Phase 1: API response contract changes
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
gateway/
├── rate_limiter.py      # MODIFY: Replace regex JWT check with verify_jwt_token()
├── main.py              # MODIFY: Strip error_type and message from 500 response
├── algod_client.py      # MODIFY: Add explicit shell=False to subprocess.run
└── auth.py              # READ ONLY: Import verify_jwt_token (no changes)

tests/
├── test_rate_limiter.py # MODIFY: Update fake-token bypass test, add real-JWT test
└── test_main_unit.py    # CHECK: Verify no assertions on error_type/message fields
```

**Structure Decision**: All changes are within the existing `gateway/` module and `tests/` directory. No new files, modules, or packages needed.

## Complexity Tracking

No constitution violations to justify.
