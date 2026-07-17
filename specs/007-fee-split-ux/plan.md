# Implementation Plan: Platform Fee Splits Pre-Signed Validation in Web3 UX

**Branch**: `007-fee-split-ux` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-fee-split-ux/spec.md`

## Summary

Add a confirmation modal in the AlgoBounty dashboard frontend that displays the fee split breakdown (Developer Royalty 1%, Platform Treasury 1%, Mediator Fee 0.25%, Claimant Payout) **before** the creator signs the "Approve & Release" transaction. Extend the gateway API `getApproveTxn` endpoint to return a `fee_breakdown` object. Also add the same modal for dispute resolution flows (PAYOUT, REFUND, SPLIT).

## Technical Context

**Language/Version**: Python 3.12 (FastAPI backend), TypeScript 5.x / Next.js 14+ (frontend dashboard)

**Primary Dependencies**: 
- Backend: FastAPI, SQLAlchemy async, algosdk, pyteal/Puya compiled contracts
- Frontend: React 18, wagmi (wallet connection), react-hot-toast (notifications), Tailwind CSS

**Storage**: PostgreSQL (production, `postgresql+asyncpg://`) / SQLite (local, `sqlite:///algobounty.db`)

**Testing**: pytest (backend), Vitest + React Testing Library (frontend)

**Target Platform**: GCP Cloud Run (backend), Vercel/standalone (frontend dashboard)

**Project Type**: Web application (backend API + Web3 frontend)

**Performance Goals**: Modal must render within 100ms of trigger; API response must include `fee_breakdown` within 50ms of existing `getApproveTxn` latency.

**Constraints**: Fee calculations must use the exact same integer-division floor logic as the escrow contract (`royalty = treasury = escrow * 2 // 100 // 2`, `mediator = escrow * 25 // 10000`, `claimant = escrow - royalty - treasury - mediator`). Frontend must display ALGO (not micro-ALGO). WCAG 2.1 AA compliance required.

**Scale/Scope**: Single feature — one new modal component, one API response field extension, one new hook for fee calculations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [X] **Smart Contract Language**: No smart contract changes — this is a frontend + API visibility feature. The contract's `_send_fee_split()` from #006 already handles the actual fee routing on-chain.
- [X] **RekeyTo Protection**: No state-modifying contract methods affected.
- [X] **Box Storage Limits**: No box storage changes.
- [X] **Karma Ledger Gatekeeping**: No karma interactions — purely display logic.
- [X] **Escrow Funding Verification**: No funding logic changes.
- [X] **Atomic Payout Group**: No changes to the atomic group structure. The transaction group is already built correctly; we just display its breakdown before signing.
- [X] **OIDC Security**: No OIDC changes.
- [X] **Database Compatibility**: No database changes — `fee_breakdown` is computed on-the-fly, not persisted.
- [X] **Continuous Worker Setup**: No worker changes.
- [X] **Rule 6.1 — Least-Privilege Wallet**: This feature DIRECTLY COMPLIES with Rule 6.1 by ensuring all transaction details are displayed to the user before signature.

**Verdict**: All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/007-fee-split-ux/
├── plan.md              # This file
├── research.md          # Phase 0 output (no research needed — no unknowns)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contract for extended getApproveTxn response)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
frontend/                          # Next.js dashboard
├── src/
│   ├── components/
│   │   ├── approve-modal.tsx      # NEW: Fee split confirmation modal
│   │   ├── dispute-modal.tsx      # MODIFIED: Existing dispute modal with fee breakdown
│   │   └── fee-breakdown-table.tsx # NEW: Shared fee breakdown display component
│   ├── hooks/
│   │   └── useFeeBreakdown.ts     # NEW: Client-side fee calculation hook
│   └── services/
│       └── api.ts                 # MODIFIED: Extend getApproveTxn response type
│
backend/                           # FastAPI gateway (or gateway/)
├── src/                           # or gateway/
│   ├── api/                       # or app/ routes
│   │   └── bounties.py            # MODIFIED: getApproveTxn endpoint returns fee_breakdown
│   └── models/                    # or schemas/
│       └── fee.py                 # NEW: Fee calculation models/types
│
tests/
├── frontend/
│   └── approve-modal.test.tsx     # NEW: Component tests
└── backend/
    └── test_fee_breakdown.py      # NEW: Fee calculation tests
```

**Structure Decision**: AlgoBounty follows a standard Web3 full-stack layout with a Next.js frontend (`dashboard/`) and FastAPI backend (`gateway/`). The fee breakdown modal lives in the frontend component tree; the API extension lives in the gateway route handler.

## Complexity Tracking

No complexity violations. This is a straightforward UI + API extension feature with no architectural changes to the smart contract or backend state machine.
