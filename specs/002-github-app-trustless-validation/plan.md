# Implementation Plan: GitHub App Integration & Trustless Payout Validation

**Branch**: `002-github-app-trustless-validation` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-github-app-trustless-validation/spec.md`

## Summary
The goal is to implement and validate the trustless payout workflow (`is_hitm = 0`) orchestrated by the GitHub App integration. On a GitHub pull request merge event, the gateway will capture the webhook, map it to an active bounty, and automatically execute the on-chain payout transaction to release the funds.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, SQLAlchemy, py-algorand-sdk

**Storage**: Supabase / PostgreSQL (Production), SQLite (Local Dev)

**Testing**: pytest, pytest-asyncio

**Target Platform**: Algorand Sandbox (LocalNet), GCP Cloud Run

**Project Type**: web-service / API integration

**Performance Goals**: Webhook acknowledgement response time < 500ms

**Constraints**: < 200ms p95 response time for API endpoints, single-instance background workers

**Scale/Scope**: Automated GitHub event sync for repository branches

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Smart Contract Language**: Written in Algorand Python (Puya).
- [x] **RekeyTo Protection**: Verified RekeyTo checks in contract logic.
- [x] **Box Storage Limits**: Keys/sizes inside boxes are restricted.
- [x] **Karma Ledger Gatekeeping**: Integrated with the Karma Ledger.
- [x] **Escrow Funding Verification**: Implements transaction group validation and balance checks.
- [x] **Atomic Payout Group**: Payout operations are structured as atomic groups.
- [x] **OIDC Security**: GitHub OIDC JWT verification verified.
- [x] **Database Compatibility**: Supports PostgreSQL (asyncpg) and SQLite.
- [x] **Continuous Worker Setup**: Configured for Cloud Run continuous execution.

## Project Structure

### Documentation (this feature)

```text
specs/002-github-app-trustless-validation/
├── plan.md              # This file
├── research.md          # Webhook signature/event research
├── data-model.md        # DB schema modifications for linking
├── quickstart.md        # Mock payload and API testing guide
└── contracts/
    └── interfaces.md    # Webhook path and JSON schema payload format
```

### Source Code (repository root)

```text
gateway/
├── routers/
│   └── github.py        # Handles the /webhooks/github endpoint
├── database.py          # SQLAlchemy models
├── worker.py            # Async tasks for on-chain dispatch
└── main.py              # API entry point
```

**Structure Decision**: Code changes are concentrated in the `gateway/` project layer, keeping with the FastAPI project setup.
