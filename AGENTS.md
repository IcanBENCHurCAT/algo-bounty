# AlgoBounty — AI Agent Guidelines (AGENTS.md)

Welcome, autonomous agents and sub-agents, to the **AlgoBounty** repository. This document serves as your operational manual for contributing to this codebase.

## 1. Project Context

**AlgoBounty** is a decentralized bounty platform built on the **Algorand** blockchain. It facilitates autonomous multi-agent task execution and payout. Think of it like GitHub Sponsors or Upwork, but purpose-built for AI agents.

Key features:
*   **On-chain escrow** (ALGO or ASAs)
*   **Reputation system** (Karma scoring)
*   **Human-in-the-middle (HITM)** review option
*   **GitHub integration** (Bounties tied to PRs/issues)

This project is a successor to the failed "Rust Chain" project and is explicitly designed to solve its failure modes by leveraging an existing, robust blockchain (Algorand) rather than building custom consensus/state machines.

## 2. Architecture & Tech Stack

You are working in a hybrid Web3 environment. The tech stack is non-negotiable:

*   **Smart Contracts:** Algorand Python (`puya` compiler) targeting AVM 12+. (Do **not** use legacy PyTeal).
*   **Backend Gateway:** FastAPI (Python 3.12+).
*   **Database:** Supabase PostgreSQL (production) / SQLite (local dev MVP).
*   **Blockchain Interaction:** PyAlgoSDK, AlgoKit.
*   **Events:** Server-Sent Events (SSE) via Redis/FastAPI.
*   **Auth:** Ed25519 Wallet Signatures + JWT (No passwords).

## 3. Core Directives & Rules

When modifying code in this repository, you **must** adhere to the following rules:

### 3.1. Smart Contract Development
*   **Use Puya:** All new contract code must use the Algorand Python compiler (`puya`), not legacy PyTeal.
*   **No Centralized Escrow:** Smart contracts cannot hold funds indefinitely without a release mechanism. Bounties must have timeout fallbacks (auto-release or auto-refund).
*   **State is Immutable:** Rely on the AVM for state guarantees. Do not attempt to track on-chain balances in the SQL database as a source of truth; use the Indexer or Node API.
*   **Security First:** Always verify funding (e.g., `_verify_escrow_funding`) and validate inputs (e.g., box sizes).

### 3.2. Backend Development (Gateway)
*   **Idempotency:** Webhook handlers (especially GitHub) must be idempotent.
*   **No "Bridge" Logic:** Algorand uses atomic transfers. Do not implement complex deposit/withdrawal queues in the backend. If a transaction group succeeds, it succeeds entirely.
*   **Karma is King:** Respect the karma system. Bounties have access tiers based on karma. Do not bypass these checks in the API.

### 3.3. Avoiding Past Mistakes (The "Rust Chain" Lessons)
*   **No Custom Blockchains:** Do not attempt to build custom consensus or transaction mempools.
*   **No Opaque Verification Traps:** Do not implement scrambled math or custom CAPTCHAs for on-chain identity. Wallet signatures are the only valid form of authentication.
*   **No Centralized Billing Blockers:** The system must be self-funding via wallet transactions. Do not introduce dependencies on centralized billing accounts (like a single GCP service account for payouts).

## 4. Development Workflow & Testing

### 4.1 Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install algokit
```

### 4.2 Running Tests
Before submitting any code, you must ensure the test suite passes.
```bash
export PYTHONPATH="."
pytest tests/ -v
```

### 4.3 Contract Compilation
If you modify `escrow.algo`, you must recompile it to TEAL:
```bash
python compile_teal.py
# OR if using algokit directly:
algokit compile escrow.algo -o escrow.teal
```

## 5. Directory Structure
*   `/dashboard`: Legacy/Current frontend (Next.js/Svelte)
*   `/gateway`: FastAPI backend API
*   `/supabase`: Database migration scripts and RLS policies
*   `/tests`: Integration and unit tests
*   `escrow.algo`: The core smart contract
*   `v*-*.md`: Historical design and architecture documents (read these if you need context on specific features).

**Remember:** Your goal is autonomous execution, but not at the cost of correctness or security. Verify your assumptions by reading the design documents (e.g., `v1-teal-escrow-contract.md`) before changing core logic.