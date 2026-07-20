# Implementation Plan: 003-byoa-github-integration

**Branch**: `003-byoa-github-integration` | **Date**: 2026-07-20 | **Spec**: [link](spec.md)

**Input**: Feature specification from `/specs/003-byoa-github-integration/spec.md`

## Summary

Update gateway configuration and GitHub logic to enforce GitHub App authentication. Track the authorized Gateway/App per-bounty or enforce HITM (Human-in-the-Middle) mode for community-hosted nodes. Securely bind issue, repo, and actor during webhook processing.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, PyGithub, httpx, Algorand SDK, Supabase

**Storage**: PostgreSQL (Supabase) / SQLite

**Testing**: pytest

**Target Platform**: Linux (Docker / GCP Cloud Run)

**Project Type**: web-service (Gateway API backend)

**Performance Goals**: < 1s latency for webhook processing

**Constraints**: Must maintain backward compatibility with existing HITM mode flows

**Scale/Scope**: Handles webhooks for multiple decentralized deployments

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Smart Contract Language**: Are all smart contracts written in Algorand Python and compiled via the Puya compiler? (AVM 12+)
- [x] **RekeyTo Protection**: Are all state-modifying contract methods protected by RekeyTo checks (`Txn.rekey_to() == Account(0)`)?
- [x] **Box Storage Limits**: Are keys and storage sizes inside boxes strictly limited?
- [x] **Karma Ledger Gatekeeping**: If the feature creates or claims bounties, does it integrate with the Karma Ledger and enforce karma tier rules?
- [x] **Escrow Funding Verification**: Does it implement dual-layer verification for funding new escrows?
- [x] **Atomic Payout Group**: Are all payout, refund, or split operations structured as atomic groups?
- [x] **OIDC Security**: Are GitHub Actions automated tests validated securely using GitHub JWKS OIDC tokens, or bypassed safely using HITM?
- [x] **Database Compatibility**: Do database operations support both production PostgreSQL and local SQLite?
- [x] **Continuous Worker Setup**: Does the background worker/indexer run continuously in a non-throttled GCP Cloud Run environment?
- [x] **Mediator Fee Safety Net**: If the feature touches payouts, fees, or claims, does it implement the safety nets?

## Project Structure

### Documentation (this feature)

```text
specs/003-byoa-github-integration/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
gateway/
├── config.py
└── github.py

escrow.algo
```

**Structure Decision**: Option 2 (Gateway is the backend API handling GitHub webhooks).

## Complexity Tracking

None needed.
