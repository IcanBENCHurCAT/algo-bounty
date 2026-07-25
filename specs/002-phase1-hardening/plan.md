# Implementation Plan: Phase 1 Pre-Mainnet Hardening

**Branch**: `002-phase1-hardening` | **Date**: 2026-07-25 | **Spec**: [spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/002-phase1-hardening/spec.md)

**Input**: Feature specification from `specs/002-phase1-hardening/spec.md`

## Summary

Harden the AlgoBounty escrow state machine, add a manual GitHub sync endpoint with pull-model payouts, rename all "arbitrator" references to "evaluator," gate dispute resolution behind admin stewardship for Phase 1, replace automated karma penalties with a quarantine state + 72hr admin review, and document the refund lock policy in the UI and spec.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/Next.js (frontend), Algorand Python / Puya (smart contract)

**Primary Dependencies**: FastAPI, SQLAlchemy, py-algorand-sdk, Next.js 14, Tailwind CSS

**Storage**: PostgreSQL (Supabase prod) / SQLite (local dev)

**Testing**: pytest, pytest-asyncio

**Target Platform**: Linux server (GCP Cloud Run), Algorand Testnet/Mainnet

**Project Type**: Web service (gateway API) + Web3 frontend (dashboard) + Smart contract (escrow)

**Performance Goals**: Standard web app expectations; manual sync completes < 2 minutes

**Constraints**: AVM opcode limits, Algorand 3.3s block time, smart contract upgrade requires redeployment

**Scale/Scope**: Early-stage platform (tens to low hundreds of users)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Smart Contract Language**: All smart contracts are written in Algorand Python and compiled via the Puya compiler (AVM 12+). The `escrow.py` contract uses `algopy` imports.
- [x] **RekeyTo Protection**: All state-modifying contract methods verify `Txn.rekey_to == Account(Bytes(32 * b"\x00"))`. Verified across `create_bounty`, `claim_bounty`, `submit_work`, `approve_work`, `reject_work`, `submit_dispute`, `vote_dispute`, `resolve_dispute`, `claim_abandoned`, `register_arbitrator`, `deregister_arbitrator`.
- [x] **Box Storage Limits**: Box key sizes are bounded. Proof URL <= 512 bytes (`MAX_URL_BYTES`), Proof Data <= 2048 bytes (`MAX_PROOF_BYTES`), Dispute Reason <= 256 bytes (`MAX_DISPUTE_REASON_BYTES`).
- [x] **Karma Ledger Gatekeeping**: Karma is checked in the gateway layer (>= 50 for evaluator registration). On-chain enforcement is deferred to Phase 2.
- [x] **Escrow Funding Verification**: `_verify_escrow_balance()` performs balance checks before all payouts. Contract creation validates `escrow_amount > 0`.
- [x] **Atomic Payout Group**: All payouts use Algorand Inner Transactions (`itxn`) issued by the contract as sender.
- [x] **OIDC Security**: OIDC verification exists in `gateway/oidc.py` and `escrow.py` (`github_verify`).
- [x] **Database Compatibility**: `gateway/database.py` supports both PostgreSQL (`postgresql+asyncpg://`) and SQLite (`check_same_thread=False`).
- [x] **Continuous Worker Setup**: `gateway/worker.py` runs as a continuous background loop polling every 10 seconds.
- [x] **Mediator Fee Safety Net**: `_send_fee_split()` redirects the 0.25% mediator fee to the worker under HITM mode or when no dispute is invoked.

**All 10 gates pass. Proceeding to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/002-phase1-hardening/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 validation guide
├── contracts/           # Phase 1 interface contracts
│   ├── escrow-state-machine.md
│   ├── sync-github-api.md
│   └── quarantine-api.md
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
# Smart Contract Layer
escrow.py                          # [MODIFY] State machine hardening + evaluator rename

# Gateway (Backend)
gateway/
├── routers/
│   ├── arbitrators.py             # [RENAME → evaluators.py] + route prefix change
│   ├── bounties.py                # [MODIFY] Add sync-github endpoint
│   └── admin.py                   # [NEW] Admin dispute resolution + quarantine review
├── schemas.py                     # [MODIFY] Rename Arbitrator* → Evaluator*, add quarantine schemas
├── supabase_migration.py          # [MODIFY] Rename tables + add quarantine model
├── database.py                    # [MODIFY] Import updated model names
├── main.py                        # [MODIFY] Mount renamed router + new admin router
├── github.py                      # [MODIFY] Add sync-github verification logic
└── worker.py                      # [MODIFY] Update log string references from arbitrator → evaluator

# Dashboard (Frontend)
dashboard/src/
├── app/
│   ├── mediators/page.tsx         # [MODIFY] Rename arbitrator API calls → evaluator
│   └── bounties/[id]/page.tsx     # [MODIFY] Add refund lock indicator + sync button
├── components/
│   ├── DashboardLayout.tsx        # [MODIFY] Rename nav items if needed
│   └── RefundLockNotice.tsx       # [NEW] Refund lock policy notice component
└── lib/
    └── api.ts                     # [MODIFY] Rename arbitrator API types → evaluator, add sync endpoint

# Tests
tests/
├── test_arbitrators.py            # [RENAME → test_evaluators.py]
├── test_sync_github.py            # [NEW]
├── test_quarantine.py             # [NEW]
└── test_admin_disputes.py         # [NEW]
```

**Structure Decision**: Web application (Option 2) with separate backend (`gateway/`) and frontend (`dashboard/`) plus a smart contract layer (`escrow.py`). No new top-level directories needed.

## Complexity Tracking

> No Constitution Check violations. No complexity justifications needed.

