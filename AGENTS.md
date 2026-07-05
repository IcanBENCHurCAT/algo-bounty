# AGENTS.md — Agent Guide for AlgoBounty

Welcome, fellow agent. This document is designed to help you navigate and contribute to the AlgoBounty project efficiently. AlgoBounty is a decentralized bounty platform built on Algorand, facilitating autonomous multi-agent task execution and payout.

---

## 1. Project Overview

AlgoBounty consists of three main layers:
- **Smart Contracts**: On-chain escrow logic written in Puya/pyTEAL (`escrow.algo`).
- **Gateway (Backend)**: A FastAPI service that orchestrates between the blockchain, the database, and external integrations like GitHub (`gateway/`).
- **Dashboard (Frontend)**: A Next.js web application for users to interact with the platform (`dashboard/`).

### Core Architecture
- **Database**: Supabase PostgreSQL (Production) / SQLite (Local Dev fallback).
- **Chain**: Algorand (Testnet/Mainnet).
- **Auth**: Wallet signature-based authentication + JWT. Supports Pera, Defly, and Edge wallets.
- **OIDC**: GitHub Actions OIDC token verification for automated bounty claiming and submission.
- **Events**: Real-time marketplace updates via Server-Sent Events (SSE).

---

## 2. Directory Structure

```text
.
├── gateway/                # FastAPI Backend
│   ├── algod_client.py     # Algorand blockchain client
│   ├── auth.py             # Wallet signature & JWT logic
│   ├── database.py         # SQLAlchemy models & DB init
│   ├── github.py           # GitHub webhook & bot logic
│   ├── main.py             # FastAPI entry point & routes
│   └── supabase_migration.py # Supabase/Postgres setup
├── dashboard/              # Next.js Frontend (App Router)
├── supabase/               # Database RLS policies
├── tests/                  # Backend test suite
├── escrow.algo             # Main Smart Contract (Puya/pyTEAL)
├── v0-v7-*.md              # Design Documents (READ THESE FIRST)
└── CONTRACTOR-BRIEF.md      # High-level implementation roadmap
```

---

## 3. Tech Stack & Key Libraries

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, Pydantic, `py-algorand-sdk`.
- **Frontend**: Next.js, TypeScript, Tailwind CSS.
- **Database**: PostgreSQL (Supabase), Alembic for migrations.
- **Linting/Formatting**: `ruff` for Python.

---

## 4. Operational Tips for Agents

### Development Environment
- Always use a virtual environment.
- Install dependencies: `pip install -r requirements.txt`.
- Set up `.env` in `gateway/` based on `.env.template`.

### Running with Docker Compose (Local Dev & Demo)
A centralized `docker-compose.yml` is provided at the project root to orchestrate the gateway (FastAPI), worker/indexer, and dashboard (Next.js) seamlessly using a local SQLite database fallback:
```bash
# Build and start all services (Gateway at http://localhost:8000, Dashboard at http://localhost:3000)
docker-compose up --build

# Run in background
docker-compose up -d
```
- **Quirk: Client API Routing**: The frontend (`dashboard`) is built with `NEXT_PUBLIC_API_URL=http://localhost:8000`. Since queries originate from the user's browser, the frontend container must point to the *host's* localhost port `8000` rather than the docker network alias `gateway`.
- **Quirk: Supabase Mocking**: The Next.js middleware initiates Supabase clients. For local SQLite mode, dummy credentials (`NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`) are passed via environment variables to bypass client initialization checks since the database queries go entirely to the Gateway API.

### Local Algorand Sandbox (LocalNet) Setup
To test on-chain features locally, run a local Algorand development node (LocalNet) on your host machine.

#### Option A: Using AlgoKit (Recommended)
The official and modern way to run a local network is using the **AlgoKit CLI**:
1. Install AlgoKit (requires Python and pipx): `pipx install algokit`
2. Start LocalNet: `algokit localnet start`
3. Stop LocalNet: `algokit localnet stop`

#### Option B: Using the Legacy Sandbox
If you prefer the original sandbox:
1. Clone the repository: `git clone https://github.com/algorand/sandbox.git`
2. Start it: `./sandbox up` (runs on default dev private network ports `4001` and `8980`)

The gateway services inside Docker connect to the host's LocalNet/Sandbox via `http://host.docker.internal` automatically.

### Running the Gateway & Worker (Standalone)
```bash
# Run the API server
export PYTHONPATH=.
python gateway/main.py

# Run the background indexer worker
export PYTHONPATH=.
python gateway/worker.py
```

### Running Tests
Use `pytest` and ensure `PYTHONPATH` is set to the root directory:
```bash
PYTHONPATH=. python -m pytest tests/
```

### Working with the Database
- The primary DB is Supabase. If `SUPABASE_URL` is missing, it falls back to `algobounty.db` (SQLite).
- Use Alembic for migrations: `alembic -c gateway/alembic.ini upgrade head`.
- Check `gateway/supabase_migration.py` for the canonical SQLAlchemy models.
- RLS policies are located in `supabase/rls_policies.sql`.

### Configuration & Secrets
- All secrets and configuration are centralized in `gateway/config.py`.
- In production, ensure `SECRET_KEY`, `PLATFORM_PRIVATE_KEY`, and `GITHUB_TOKEN` are provided via environment variables or a configured secret manager.

### Smart Contract Integration
- The contract is in `escrow.algo`.
- Integration logic resides in `gateway/algod_client.py`.
- Frontend uses `createBounty` API which triggers deployment flows.

### Frontend Hooks
- `useWallet`: Manages connection to Pera, Defly, and Edge wallets.
- `useEvents`: Subscribes to `/api/v1/events` SSE and triggers callbacks for real-time updates.

### HITM Mode
When `is_hitm=True`, the contract sets a `review_deadline`. If the creator doesn't act, the `indexer_polling_task` detects the `auto_released_hitm` log and updates the DB.

### Karma System (v2)
Karma changes are applied both in `gateway/routers/bounties.py` (for API-driven actions) and `gateway/main.py` (for on-chain timeouts/logs).

### Middleware Implementation
- When adding middleware to the Gateway, inherit from `starlette.middleware.base.BaseHTTPMiddleware` to avoid signature mismatches.

---

## 5. Design Documents Reference

Before implementing features, consult the corresponding design document:
- **v0**: Rust Chain Autopsy (forensic analysis of prior project failures).
- **v1**: TEAL Escrow Contract spec.
- **v2**: Karma/Reputation System.
- **v3**: Verification via wallet signatures (covered in v0 and v2).
- **v4**: Dashboard & API spec.
- **v5**: GitHub Integration (The Bridge).
- **v6**: Human-in-the-Middle (HITM) Mode.
- **v7**: Project Handover (see CONTRACTOR-BRIEF.md).

---

## 6. Coding Conventions

- **Python**: Follow PEP 8. Use type hints. Use `ruff` for linting.
- **Frontend**: Use functional components and hooks. Follow the Next.js App Router conventions.
- **Security**: Never hardcode secrets. Use environment variables. Verify all blockchain interactions.

---

## 7. GitHub App Setup

For enhanced integration, it is recommended to use a GitHub App instead of a personal `GITHUB_TOKEN`.

### Required Permissions
- **Repository Permissions**:
  - **Issues**: Read & write (to post comments and manage labels)
  - **Pull requests**: Read & write (to link PRs and post status updates)
  - **Metadata**: Read-only (required by default)
- **Organization Permissions**: (Optional, if using organization-level features)
- **Events**:
  - **Issues**
  - **Issue comment**
  - **Pull request**
  - **Pull request review**

### Configuration
Set the following environment variables in your `.env` file:
- `GITHUB_APP_ID`: Your GitHub App ID.
- `GITHUB_PRIVATE_KEY`: Your App's private key (content or path to `.pem` file).
- `GITHUB_INSTALLATION_ID`: The installation ID for the repository.
- `GITHUB_WEBHOOK_SECRET`: The secret used to sign webhook payloads.

---

## 8. Current Implementation Status (Updated 2026-07-05)

### ✅ Completed
- **Smart Contract**: `escrow.algo` (748 lines Puya) compiled to TEAL (`EscrowContract.approval.teal`, `EscrowContract.clear.teal`). Use `algokit compile py escrow.algo` or run `python compile_teal.py`.
- **Backend Gateway**: FastAPI with 32 endpoints, Supabase DB, SSE broker, rate limiting, security middleware, Alembic migrations.
- **Frontend Dashboard**: Next.js with Pera/Defly/Edge wallet connect, bounty creation flow, real-time SSE updates, Profile & Notifications pages.
- **GitHub Integration**: Webhook handler with HMAC verification, OIDC bridge for automated payouts, live PR/issue linking.
- **Security**: JWT secret required (no fallback), MOCK_SIG bypass removed, HMAC verification, CORS, rate limiting, security headers.
- **Tests**: 94/95 passing. One known failure: `test_compile_escrow_contract_docstring_fallback` in `test_algod_client.py` (brittle assertion).
- **CI/CD**: GitHub Actions workflow, Dockerfile, Cloud Run deploy scripts.

### 🔴 Priority 1 — Must Do First
1. **Real on-chain integration** (`gateway/algod_client.py`): Bounty creation, claim, submit, approve/reject are DB-only. Need PyAlgoSDK to deploy escrow contract and execute real transactions on testnet.
2. **Indexer background task** (`gateway/indexer.py`): `poll_bounty_events()` exists but no scheduler runs it. Chain state never syncs to DB. Add APScheduler or similar.
3. **Fix test failure**: `tests/test_algod_client.py::test_compile_escrow_contract_docstring_fallback` — assertion expects string but gets None.

### 🟡 Priority 2 — Important
4. **Full GitHub webhook flow**: `gateway/github.py` handler exists, but bot commenting and PR→bounty linking are stubs (`log_bot_comment` just prints).
5. **Frontend on-chain status**: Dashboard shows DB state, not real escrow status. Wire up on-chain data display.
6. **Expand test suite**: Target 80%+ coverage. Currently minimal on escrow edge cases (timeouts, disputes, ghosting scenarios).
7. **Bulk transaction search**: Optimize `indexer_polling_task` to use single `search_transactions` call for all app IDs.

### 🔵 Priority 3 — Nice to Have
8. **Active cleanup triggering**: Gateway should actively call on-chain methods (`expire_claim`, `auto_release`, `timeout_dispute`) when internal deadlines hit.
9. **Defly/Edge wallet on-chain status**: Wallet selection menu exists but needs real integration for those wallets.

### Key Files for Contractors
- **Smart contract**: `escrow.algo` (Puya source), `compile_teal.py` (build script), `EscrowContract.approval.teal` (compiled output)
- **On-chain interaction**: `gateway/algod_client.py` — health check, balance, holders, compile — needs tx execution
- **Bounty lifecycle**: `gateway/main.py` — all CRUD + claim/submit/approve/reject/dispute endpoints
- **Indexer**: `gateway/indexer.py` — polling functions, needs scheduler
- **Tests**: `tests/` — 19 test files, 94 passing

---

*Keep this document updated as the project evolves.*
