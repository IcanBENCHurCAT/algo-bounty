<!--
Sync Impact Report:
- Version change: TEMPLATE -> 1.0.0
- List of modified principles:
  - [PRINCIPLE_1_NAME] -> I. Smart Contract Escrow (TEAL State Machine)
  - [PRINCIPLE_2_NAME] -> II. On-Chain Karma Ledger Gatekeeping
  - [PRINCIPLE_3_NAME] -> III. Strict Escrow Funding & Balance Verification
  - [PRINCIPLE_4_NAME] -> IV. Secure Atomic Payout Group Execution
  - [PRINCIPLE_5_NAME] -> V. Automated Verification & OIDC Bridge
- Added sections:
  - Development & Security Constraints (replacing SECTION_2)
  - Testing Discipline & Environment Setup (replacing SECTION_3)
- Removed sections: None
- Templates requiring updates:
  - ✅ plan-template.md (.specify/templates/plan-template.md)
  - ✅ tasks-template.md (.specify/templates/tasks-template.md)
- Follow-up TODOs: None (all placeholders resolved)
-->

# AlgoBounty Constitution

## Core Principles

### I. Smart Contract Escrow (TEAL State Machine)
Every bounty lifecycle is strictly enforced on-chain via an 8-state TEAL smart contract application written in Algorand Python (Puya). All state transitions, deadlines, and payouts must be validated by the contract's logic; bypasses or off-chain state deviations are strictly prohibited.

### II. On-Chain Karma Ledger Gatekeeping
Access to create and claim bounties is governed by the shared Karma Ledger. New or unverified addresses (karma < 10) are restricted to Human-in-the-Middle (HITM) mode. Karma updates (+5 for payouts, -5 for ghosting/abandonment, -20 for expired claims) are executed atomically with escrow completion calls.

### III. Strict Escrow Funding & Balance Verification
All bounties must undergo strict dual-layer verification at creation: transaction group validation to confirm the preceding transaction funds the application account with the exact escrow amount, and application balance checks to verify the funds are locked. Fake escrows are prohibited.

### IV. Secure Atomic Payout Group Execution
Smart contracts cannot initiate payments unilaterally. All payouts, refunds, and splits must be executed as atomic group transactions containing the application call and the contract-as-sender payment transaction, ensuring that state transitions and payouts fail or succeed together.

### V. Automated Verification & OIDC Bridge
To enable trustless payouts, automated testing verification is integrated with GitHub Actions. The off-chain worker validates GitHub OIDC JWT tokens against GitHub's JWKS before updating the contract's verification status, ensuring secure, code-driven payout logic.

## Development & Security Constraints

- **RekeyTo Protection**: Every state-modifying smart contract method must verify that `Txn.rekey_to()` is not modified (`Account(0)`), preventing account takeover.
- **Box Storage Limitations**: Keys and storage sizes inside boxes must be strictly limited (Proof URL <= 512 bytes, Proof JSON <= 2048 bytes, Dispute Reason <= 256 bytes) to prevent Denial-of-Service and memory bloating.
- **Dual Database Architecture**: The FastAPI gateway must support PostgreSQL in production (with asynchronous client engines using `postgresql+asyncpg://`) and SQLite locally.
- **Background Worker Durability**: The background indexer must run continuously in a non-throttled single-instance GCP Cloud Run environment.

## Testing Discipline & Environment Setup

- **Automated Testing Requirements**: All smart contract updates, gateway endpoints, and background worker logic must be covered by Jest/Vitest (frontend) or pytest/pytest-asyncio (backend) tests.
- **CI rate-limiting bypass**: CI tests must set the environment variable `TESTING="True"` to bypass API rate limits and enable mock suites.
- **Frontend Routing Quirk**: Next.js dashboard routing must point client requests to the host's localhost port 8000 (rather than internal container aliases) since requests originate from the user's browser.

## Governance

- Bounties must follow a 2% treasury fee collection policy on payouts.
- Dispute resolution requires cryptographic verification of the mediator signature (`op.ed25519verify`) against the mediator address stored at bounty creation.
- Constitutional amendments require version bumps under semantic versioning rules:
  - **MAJOR**: Backward-incompatible smart contract state or logic changes, or removal of key principles.
  - **MINOR**: Addition of new principles or major system features (e.g. adding new karma tier rules).
  - **PATCH**: Non-functional refactorings, clarifications, or template sync fixes.
- All ratification and amendment dates must be maintained in ISO format (YYYY-MM-DD).
- Changes must be propagated across all dependent template files (`plan-template.md`, `spec-template.md`, `tasks-template.md`).

**Version**: 1.0.0 | **Ratified**: 2026-07-13 | **Last Amended**: 2026-07-13
