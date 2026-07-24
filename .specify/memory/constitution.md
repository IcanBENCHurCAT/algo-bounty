<!--
SYNC IMPACT REPORT:
- Version change: 2.5.0 -> 3.0.0
- Ratification Date: 2026-07-16
- Last Amended Date: 2026-07-19 (v3.0.0)
- Modified Sections:
  - Sections 2.4, 3.1, 3.3, and 5.3 generalized to remove hardcoded protocol details (box sizes, enum states, fee %).
  - Section 10 (Existing AlgoBounty Specific Rules) deleted as these mechanics are permanently baked into the protocol.
  - Review Checklist condensed to remove baked-in protocol checks.
- Templates requiring updates:
  - None.
-->

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

2.4. Keys and storage sizes inside Global/Local Boxes MUST be strictly limited to prevent Denial-of-Service and memory bloating.

2.5. Any smart contract change (including new application ID deployments, runtime parameter upgrades, or contract logic changes) MUST go through the full spec-kit process: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`, with comprehensive unit and integration testing before deployment.

### 3. Explicit State Machines and Invariants

3.1. Every stateful contract MUST enforce an explicit state machine defining the valid lifecycle transitions.

3.2. Guard functions MUST check the current state before executing logic.

3.3. Key system invariants MUST be strictly enforced on-chain (e.g. accounting balances matching expected funding, and payout splits strictly constrained).

### 4. Deterministic ABI and API Usage

4.1. All application methods MUST use Algorand ABI specifications, with arguments and return types declared and kept in sync with on-chain logic.

4.2. The Web3 frontend dashboard and off-chain services MUST consume typed client bindings or generated interfaces derived directly from the contract's ABI definition instead of using manual transaction payload construction.

### 5. Transparent Governance, Upgrades, and Platform Fee Sharing

5.1. **Deployment Architecture Roadmap**: The deployment lifecycle proceeds across three stages:

- **Stage 1 (Local Dev)**: Operates against sandbox environments and local SQLite databases.
- **Stage 2 (Staging/Beta)**: Deployed to testnet networks and serverless cloud runners (e.g., GCP Cloud Run) with Postgres.
- **Stage 3 (Production/Scale)**: Orchestrated container environments (e.g., Kubernetes) with high-availability Postgres clusters.

  5.2. Only the platform administrator account, an authorized multi-sig account, or an on-chain DAO voting contract specified during contract deployment (the platform `mediator` or platform owner key) can upgrade applications or adjust critical platform parameters (e.g., fee rates, treasury destinations).

  5.3. **Bounty Fee Collection and Treasury Distribution**: Fee collection, treasury distribution, and mediator safety nets MUST be programmatically enforced on-chain. The frontend UI MUST accurately mirror the dynamic fee distribution calculated by the contract.

  5.4. **Upgrade Path**: When upgrading contracts, migration scripts and deprecation strategies (such as freezing old contracts or migrating user boxes) MUST be defined in specs and plans prior to execution. Proxy application patterns or explicit application ID registry routers should be preferred.

  5.5. **DAO Governance Evolution (Phased Platform Cooperative)**: The platform will transition to a decentralized cooperative DAO in three phases:
- **Phase 1: Progressive Decentralization (Transition Phase)**: While the system is new and the treasury is accumulating funds, the lead developer/admin retains a stewardship role to perform emergency/administrative refunds for stuck bounties and directly fund platform-improvement bounties from the treasury. This is a temporary bootstrap measure.
- **Phase 2: Pure Governance (Compliant)**: Control transitions to the community via a 1-member-1-vote non-transferable Soulbound Token (SBT). Membership is gated by on-chain Karma (e.g., Karma > 50). This SBT governs protocol upgrades and the existing treasury without conferring financial expectation.
- **Phase 3: Economic Participation (Deferred)**: To maintain compliance with financial regulations, the issuance of any tradable economic token representing patronage dividends from platform surpluses is explicitly deferred pending comprehensive legal review. The Developer Royalty allocation remains permanently assigned to the original creator/steward account.

  5.6. **Hosted Indexer Neutrality**: To maintain neutral status and avoid classification as a commercial matching broker, any hosted platform indexer or search dashboard MUST index and display all deployments of the `EscrowContract` smart contract template. The indexer MUST NOT filter out, penalize, or hide bounties that modify default contract fee addresses, reduce platform fees to `0%`, or specify custom treasury accounts.

  5.7. **Direct Peer-to-Peer Engagement**: The platform is an open-source matching protocol and does not act as an employer, agent, or payment clearinghouse. All transactions, work agreements, and payouts are direct P2P interactions between creators and workers. All tax compliance, documentation (such as Form 1099 or DAC7), and withholding obligations are the sole responsibility of the participating counterparties and MUST be handled directly between them off-chain.

  5.8. **Stewardship of Autonomous Agents**: Because autonomous software agents lack legal personality and tax registration capabilities, any Algorand account or wallet controlled by an agent on the platform MUST have a designated human steward. The human steward assumes full legal, tax, and financial responsibility for all actions, claims, disputes, and payouts executed by their agent's wallet.

  5.9. **Self-Hosting and Open Source Licensing (AGPL 3.0)**: The platform MUST be designed to be trivially self-hostable by anyone, whether locally or in a private cloud. The architecture MUST allow operators to easily reconfigure fee routing to their own treasury accounts, apply custom UI reskins, and run autonomous deployments without relying on a central authority. The project adopts the AGPL 3.0 license to ensure that any modified or self-hosted versions of the platform—especially those offered as a service over a network—remain fully open source. This guarantees that improvements and bug fixes are shared back with the community and prevents proprietary enclosure of the core escrow and gateway logic.

  5.10. **No Proprietary Vendor Lock-in (BYOK)**: To preserve self-hostability, the platform MUST NOT hardcode or mandate the use of proprietary third-party API keys or centralized brokers for core escrow functionality (e.g., GitHub OIDC, AI services). All external integrations MUST support a "Bring Your Own Key" (BYOK) or "Bring Your Own App" configuration so that local operators are never blocked by the original author's rate limits or suspended accounts.

  5.11. **Frontend Portability and Decentralization**: The frontend Web3 application MUST be designed to be minimally reliant on a centralized backend for core smart contract interactions (creation, claiming, approval). It SHOULD support static generation/export (e.g., via Next.js `output: 'export'`) to enable hosting on decentralized storage networks like IPFS or Arweave, communicating directly with Algorand RPC nodes.

### 6. Least-Privilege Wallet and Key Management

6.1. The Web3 frontend application MUST display clear, legible transaction details (assets, application calls, exact fees, and final effects) to the user _before_ requesting a wallet signature. Hidden side effects are strictly prohibited.

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

---

## II. Preferred Guidelines (SHOULD Principles)

### 10. Frontend UX Clarity

10.1. The frontend SHOULD make blockchain actions understandable to non-expert users: displaying transaction fees, wait times, current application state (e.g., bounty lifecycle, governance phase), and friendly, human-readable error messages.

### 11. Accessibility and Inclusivity

11.1. The user experience SHOULD follow standard accessibility guidelines (WCAG 2.1 AA) and remain fully usable for non-technical community participants to encourage open, decentralized contribution.

### 12. Developer Ergonomics

12.1. The codebase SHOULD provide local development tools (e.g., sandbox configs, AVM test scripts, local SQLite migration helpers, and mock web servers) to allow developers and agents to verify changes quickly.

### 13. Documentation and ADRs

13.1. Major structural updates, smart contract rewrites, or governance changes SHOULD be recorded as Architecture Decision Records (ADRs) under `docs/adr/` and linked directly in the constitution.

### 14. Systematic Performance Optimization

14.1. Optimization work SHOULD be guided by precise metrics (AVM opcode counts, transaction sizes, latency benchmarks) rather than premature micro-optimizations that reduce code readability.

### 15. Composability and Interoperability

15.1. System designs SHOULD utilize native Algorand primitives (ASAs, inner transactions, atomic transfer groups) rather than building bespoke logic from scratch.

### 16. Configuration and Feature Flags

16.1. Experimental or newly integrated features SHOULD be guarded by configuration flags or phased rollouts, with predefined rollback steps documented in plan files.

---

## Constitution Review Checklist

Agents and human contributors MUST use this checklist to validate new specs/plans before implementing:

- [ ] Does the design respect financial regulations and avoid KYC/AML bypass? (Rule 1.1)
- [ ] Are all state changes and payouts constrained by an explicit on-chain state machine? (Rule 3.1)
- [ ] Does every state-modifying method verify that `Txn.rekey_to()` is not modified? (Rule 2.3)
- [ ] Is there an explicit upgrade path or proxy strategy defined? (Rule 5.2)
- [ ] Does the frontend show users the exact transactions they are signing? (Rule 6.1)
- [ ] Are any high-risk deployment tasks gated behind human verification? (Rule 9.3)
- [ ] Do external integrations support "Bring Your Own Key" (BYOK) to prevent vendor lock-in? (Rule 5.10)
- [ ] Are core Web3 interactions operable without a centralized backend? (Rule 5.11)

---

**Version**: 3.0.0 | **Ratified**: 2026-07-16 | **Last Amended**: 2026-07-19 (v3.0.0)
**Superseded rules**: 2.5.0 core principles were updated with a phased cooperative DAO rollout. v3.0.0 removed hardcoded protocol mechanics that are now baked into the smart contract codebase, streamlining the constitution into prescriptive architectural guardrails.
