# AlgoBounty Project Constitution

## Overview
This document defines the prescriptive architectural rules, engineering standards, and governance policies for AlgoBounty, a decentralized bounty board and task execution platform. All future specifications, plans, tasks, and implementations produced by automated agents or human contributors MUST strictly comply with the principles detailed herein.

---

## I. Non-Negotiable Guardrails (MUST Principles)

### 1. Legal and Ethical Compliance
1.1. The system MUST NOT be designed to bypass financial regulations, KYC/AML obligations, or other applicable laws.
1.2. Architecture flows MUST bias toward excluding demonstrably bad actors (fraud, abuse, or regulatory violations) from executing critical actions including bounty escrow creation, claim actions, payouts, dispute arbitration, or governance participation.

### 2. Smart Contract Security and Correctness
2.1. Stateful and stateless ASC1 smart contracts MUST be written in Algorand Python (Puya) or TEAL/PyTeal and compiled targeting AVM 12+ specifications.
2.2. Contracts MUST validate all critical transaction fields strictly: verify transaction types (`pay`, `axfer`, `appl`), assert correct `sender` values, check application transaction fee bounds, and enforce safe usage of `OnComplete` codes (e.g., rejecting arbitrary `UpdateApplication` or `DeleteApplication` calls unless authorized by explicit governance).
2.3. Every state-modifying smart contract method MUST verify that `Txn.rekey_to()` remains unmodified (`Account(0)`), preventing account takeover.
2.4. Keys and storage sizes inside Global/Local Boxes MUST be strictly limited to prevent Denial-of-Service and memory bloating:
   - Proof URL: `<= 512` bytes
   - Proof JSON: `<= 2048` bytes
   - Dispute Reason: `<= 256` bytes
2.5. Any smart contract change (including new application ID deployments, runtime parameter upgrades, or contract logic changes) MUST go through the full spec-kit process: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`, with comprehensive unit and integration testing before deployment.

### 3. Explicit State Machines and Invariants
3.1. Every stateful contract MUST enforce an explicit state machine defining the valid lifecycle transitions (e.g., `INITIALIZED`, `FUNDED`, `CLAIMED`, `SUBMITTED`, `APPROVED`, `DISPUTED`, `RESOLVED`, `REFUNDED`).
3.2. Guard functions MUST check the current state before executing logic.
3.3. Key system invariants MUST be strictly enforced on-chain:
   - Escrow accounts must hold the exact funded amount required for the bounty.
   - Payout splits must sum precisely to `100%` (or the funded balance minus treasury fees).
   - Only the designated creator, claimant, or arbitrator can execute their respective actions according to state context.

### 4. Deterministic ABI and API Usage
4.1. All application methods MUST use Algorand ABI specifications, with arguments and return types declared and kept in sync with on-chain logic.
4.2. The Web3 frontend dashboard and off-chain services MUST consume typed client bindings or generated interfaces derived directly from the contract's ABI definition instead of using manual transaction payload construction.

### 5. Transparent Governance, Upgrades, and Platform Fee Sharing
5.1. **Deployment Architecture Roadmap**: The deployment lifecycle proceeds across three stages:
   - **Stage 1 (Local Dev)**: Operates against sandbox environments and local SQLite databases.
   - **Stage 2 (Staging/Beta)**: Deployed to testnet networks and serverless cloud runners (e.g., GCP Cloud Run) with Postgres.
   - **Stage 3 (Production/Scale)**: Orchestrated container environments (e.g., Kubernetes) with high-availability Postgres clusters.
5.2. Only the platform administrator account, an authorized multi-sig account, or an on-chain DAO voting contract specified during contract deployment (the platform `mediator` or platform owner key) can upgrade applications or adjust critical platform parameters (e.g., fee rates, treasury destinations).
5.3. **Bounty Fee Collection and Treasury Distribution**:
   - The platform collects a `2%` fee upon successful payout distributions.
   - Collected fees MUST be programmatically split:
     - **Developer Royalty**: `50%` of collected fees (i.e., `1%` of total payout) MUST be sent directly to the creator's wallet address (or a designated royalty account) as compensation for platform stewardship.
     - **Platform Treasury**: `50%` of collected fees (i.e., `1%` of total payout) MUST be sent to the platform treasury account to self-fund system maintenance and application improvements.
5.4. **Upgrade Path**: When upgrading contracts, migration scripts and deprecation strategies (such as freezing old contracts or migrating user boxes) MUST be defined in specs and plans prior to execution. Proxy application patterns or explicit application ID registry routers should be preferred.
5.5. **DAO Governance Evolution**: As the platform transitions to production (Stage 3), upgrades, mediator keys, and the Platform Treasury allocation MUST be managed by a DAO-governed voting model. The Developer Royalty allocation remains permanently assigned to the original creator/steward account.

### 6. Least-Privilege Wallet and Key Management
6.1. The Web3 frontend application MUST display clear, legible transaction details (assets, application calls, exact fees, and final effects) to the user *before* requesting a wallet signature. Hidden side effects are strictly prohibited.
6.2. Escrow and logic-signature accounts MUST be configured so they can only release funds under explicit, cryptographically checked conditions (e.g., verified arbitrator ed25519 signature, or matching atomic inner transactions).

### 7. Observability and Auditability
7.1. All critical state transitions, escrow creation events, payouts, refunds, and arbitrator resolutions MUST emit log events or transaction notes with predictable keys and formatting for indexers to trace.
7.2. All components, including agents, MUST maintain a chronological, versioned history of design updates, architecture changes, and task progression within the `/specs/` directory (incorporating ADRs, commits, and logs).

### 8. Performance and Resource Constraints
8.1. Smart contracts MUST optimize bytecode to fit within Algorand's opcode and execution size limits.
8.2. Expensive work (such as code validations, repository structure checks, or complex formatting) MUST be performed off-chain, with contracts verifying the results using succinct cryptographic checks (e.g., OIDC verification or hashes).

### 9. Agentic Automation Guardrails
9.1. Any AI/LLM agent operating within this workspace MUST run in a sandbox or reproducible container environment.
9.2. Agents MUST operate under least-privilege permissions, with no direct access to production secrets, deployer private keys, or wallet authorization APIs.
9.3. High-risk operations—including contract deployments to mainnet, logic upgrades, treasury fee modifications, or arbitrator re-assignment—MUST be gated behind mandatory human review and testing; agents MUST NOT deploy or execute them automatically.

### 10. Existing AlgoBounty Specific Rules (Preserved)
10.1. **On-Chain Karma Gatekeeping**: Address capabilities are governed by the shared Karma Ledger. New/unverified addresses with `karma < 10` are restricted to Human-in-the-Middle (HITM) mode. Karma updates (+5 for payouts, -5 for abandonment, -20 for expired claims) MUST be executed atomically with escrow completion calls.
10.2. **Strict Escrow Funding & Balance Verification**: New escrows require dual-layer validation at creation: transaction group validation to confirm the preceding transaction funds the application account with the exact escrow amount, and application balance checks to verify the funds are locked.
10.3. **Secure Atomic Payout Group Execution**: All payouts, refunds, and splits MUST be executed as atomic group transactions containing the application call and the contract-as-sender payment transaction, ensuring that state transitions and payouts fail or succeed together.
10.4. **Automated Verification & OIDC Bridge**: Automated testing verification is integrated with GitHub Actions. The off-chain worker validates GitHub OIDC JWT tokens against GitHub's JWKS before updating the contract's verification status.
10.5. **Database Engine**: The FastAPI gateway MUST support PostgreSQL in production (using `postgresql+asyncpg://` async engines) and SQLite locally (`sqlite:///...`).
10.6. **Worker Durability**: The background indexer MUST run continuously in a non-throttled single-instance GCP Cloud Run environment.

---

## II. Preferred Guidelines (SHOULD Principles)

### 11. Frontend UX Clarity
11.1. The frontend SHOULD make blockchain actions understandable to non-expert users: displaying transaction fees, wait times, current application state (e.g., bounty lifecycle, governance phase), and friendly, human-readable error messages.

### 12. Accessibility and Inclusivity
12.1. The user experience SHOULD follow standard accessibility guidelines (WCAG 2.1 AA) and remain fully usable for non-technical community participants to encourage open, decentralized contribution.

### 13. Developer Ergonomics
13.1. The codebase SHOULD provide local development tools (e.g., sandbox configs, AVM test scripts, local SQLite migration helpers, and mock web servers) to allow developers and agents to verify changes quickly.

### 14. Documentation and ADRs
14.1. Major structural updates, smart contract rewrites, or governance changes SHOULD be recorded as Architecture Decision Records (ADRs) under `docs/adr/` and linked directly in the constitution.

### 15. Systematic Performance Optimization
15.1. Optimization work SHOULD be guided by precise metrics (AVM opcode counts, transaction sizes, latency benchmarks) rather than premature micro-optimizations that reduce code readability.

### 16. Composability and Interoperability
16.1. System designs SHOULD utilize native Algorand primitives (ASAs, inner transactions, atomic transfer groups) rather than building bespoke logic from scratch.

### 17. Configuration and Feature Flags
17.1. Experimental or newly integrated features SHOULD be guarded by configuration flags or phased rollouts, with predefined rollback steps documented in plan files.

---

## Constitution Review Checklist
Agents and human contributors MUST use this checklist to validate new specs/plans before implementing:
- [ ] Does the design respect financial regulations and avoid KYC/AML bypass? (Rule 1.1)
- [ ] Are all state changes and payouts constrained by an explicit on-chain state machine? (Rule 3.1)
- [ ] Does every state-modifying method verify that `Txn.rekey_to()` is not modified? (Rule 2.3)
- [ ] Are box storage boundaries strictly constrained? (Rule 2.4)
- [ ] Is there an explicit upgrade path or proxy strategy defined? (Rule 5.2)
- [ ] Does the frontend show users the exact transactions they are signing? (Rule 6.1)
- [ ] Are payouts structured as atomic groups (app call + inner payment)? (Rule 10.3)
- [ ] Have all database queries been designed to support both PostgreSQL and SQLite? (Rule 10.5)
- [ ] Are any high-risk deployment tasks gated behind human verification? (Rule 9.3)

---
**Version**: 2.0.0 | **Ratified**: 2026-07-16 | **Last Amended**: 2026-07-16
**Superseded rules**: 1.0.0 core principles were reorganized and integrated directly into Section I and Section II above.
