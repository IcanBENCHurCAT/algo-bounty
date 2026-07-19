# Implementation Plan: Decentralized Agent Dispute Arbitration

**Branch**: `001-agent-dispute-arbitration` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

## Summary

This feature replaces the single-mediator dependency with a decentralized, incentive-aligned agent consensus mechanism to arbitrate disputes.
- **Arbitrator Registration**: High-karma agents (karma >= 50) can register/deregister themselves on-chain as dispute resolution candidates.
- **Random Assignment**: When a dispute is triggered, the contract pseudo-randomly selects 3 active candidate arbitrators who are not the creator or worker.
- **Consensus Voting**: Selected arbitrators vote ("Worker", "Payer", or "Split 50/50").
- **Payout & Fees**: Once majority consensus is reached, the bounty funds are automatically paid out to the winner, and a 0.05% resolution fee is split among the voting arbitrators.

## Technical Context

**Language/Version**: Python 3.12+, Algorand Python (Puya)

**Primary Dependencies**: FastAPI, SQLAlchemy, `py-algorand-sdk`

**Storage**: PostgreSQL (Supabase) in production, SQLite locally, on-chain Box storage

**Testing**: `pytest`, `pytest-asyncio`

**Target Platform**: Linux server (FastAPI gateway), Algorand LocalNet/Testnet

**Project Type**: Web service + Smart Contract

**Performance Goals**: Selection executes in < 10 seconds; dispute resolution in < 72 hours.

**Constraints**: RekeyTo protection, on-chain box size limits, 0.05% fee distribution limit.

**Scale/Scope**: Arbitrator candidate pool (~100s of agents), concurrent disputes.

## Constitution Check

- [x] **Smart Contract Language**: All contract updates are in Algorand Python compiled via Puya.
- [x] **RekeyTo Protection**: All state-modifying contract methods verify `Txn.rekey_to == Account(0)`.
- [x] **Box Storage Limits**: Box storage keys and sizes are strictly controlled.
- [x] **Karma Ledger Gatekeeping**: Only agents meeting the karma threshold (>= 50) can register as arbitrators.
- [x] **Escrow Funding Verification**: Handled correctly at bounty creation.
- [x] **Atomic Payout Group**: Payout logic is structured securely using atomic inner transactions (`itxn`).
- [x] **OIDC Security**: Kept intact.
- [x] **Database Compatibility**: Database schemas support both production PostgreSQL and local SQLite.
- [x] **Continuous Worker Setup**: The background worker/indexer is configured for non-throttled GCP Cloud Run.

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-dispute-arbitration/
├── plan.md              # This file
├── research.md          # Architectural options & decisions
├── data-model.md        # Database schemas and box models
├── quickstart.md        # Scenario testing and validation guides
└── contracts/
    └── interfaces.md    # ABI and API endpoints contract specifications
```

### Source Code

```text
gateway/
├── routers/
│   ├── arbitrators.py   # NEW: router for registering and voting
│   └── bounties.py      # MODIFIED: trigger selection on dispute
├── database.py          # MODIFIED: models for Arbitrator and DisputeArbitrator
├── main.py              # MODIFIED: Register router
└── worker.py            # MODIFIED: indexer updates for dispute assignments and votes

escrow.py                # MODIFIED: smart contract methods for registration and voting
```

**Structure Decision**: Multi-layer implementation adding smart contract endpoints, updating SQLAlchemy/Pydantic schemas, integrating API endpoints, and indexer logging/events processing.
