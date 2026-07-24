# Implementation Plan: Direct-to-Chain Fallback

**Branch**: `002-direct-to-chain-fallback` | **Date**: 2026-07-19 | **Spec**: `/specs/002-direct-to-chain-fallback/spec.md`

## Summary

Update the Next.js frontend to optionally query public Algorand indexers (e.g. AlgoNode) directly if the Gateway API is offline, providing a read-only bypass so users can still view bounties. All state-mutating actions should be disabled during this fallback mode.

## Technical Context

**Language/Version**: TypeScript, React (Next.js 16)

**Primary Dependencies**: algosdk, Next.js, React

**Storage**: Public Algorand Indexer (read-only)

**Testing**: Jest (dashboard tests)

**Target Platform**: Web (Next.js Frontend)

**Project Type**: web-service (frontend web app)

**Performance Goals**: Automatically switch to fallback mode within 3 seconds of detecting Gateway failure.

**Constraints**: Read-only display. Mutating actions must be disabled.

**Scale/Scope**: Impacts all dashboard listing and detail views.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Smart Contract Language**: Are all smart contracts written in Algorand Python and compiled via the Puya compiler? (AVM 12+) (N/A for frontend)
- [x] **RekeyTo Protection**: Are all state-modifying contract methods protected by RekeyTo checks (`Txn.rekey_to() == Account(0)`)? (N/A for frontend)
- [x] **Box Storage Limits**: Are keys and storage sizes inside boxes strictly limited (Proof URL <= 512 bytes, Proof JSON <= 2048 bytes, Dispute Reason <= 256 bytes)? (N/A for frontend)
- [x] **Karma Ledger Gatekeeping**: If the feature creates or claims bounties, does it integrate with the Karma Ledger and enforce karma tier rules? (N/A for frontend)
- [x] **Escrow Funding Verification**: Does it implement dual-layer verification (transaction group validation + application balance check) for funding new escrows? (N/A for frontend)
- [x] **Atomic Payout Group**: Are all payout, refund, or split operations structured as atomic groups (app call + contract-as-sender payment)? (N/A for frontend)
- [x] **OIDC Security**: Are GitHub Actions automated tests validated securely using GitHub JWKS OIDC tokens? (N/A for frontend)
- [x] **Database Compatibility**: Do database operations support both production PostgreSQL (`postgresql+asyncpg://`) and local SQLite? (N/A for frontend)
- [x] **Continuous Worker Setup**: Does the background worker/indexer run continuously in a non-throttled GCP Cloud Run environment? (N/A for frontend)
- [x] **Mediator Fee Safety Net**: If the feature touches payouts, fees, or claims, does it implement the safety nets (refunding the 0.25% fee to the worker under HITM or undisputed Auto modes, and only splitting/paying mediators if a dispute is mediated in Auto mode)? (N/A for frontend)
- [x] **Frontend Portability**: Is the frontend Web3 application designed to be minimally reliant on a centralized backend for core smart contract interactions? (Yes, this feature directly addresses Rule 5.11).

## Project Structure

### Documentation (this feature)

```text
specs/002-direct-to-chain-fallback/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── indexer-fallback.md
└── tasks.md
```

### Source Code

```text
dashboard/
├── src/
│   ├── components/
│   ├── hooks/
│   └── services/
└── tests/
```

**Structure Decision**: Web application (frontend only changes)

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
