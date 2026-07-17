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
│   ├── routers/            # Domain-specific FastAPI routers
│   ├── algod_client.py     # Algorand blockchain client
│   ├── auth.py             # Wallet signature & JWT logic
│   ├── broker.py           # SSE Event stream broker
│   ├── database.py         # SQLAlchemy models & DB init
│   ├── github.py           # GitHub webhook & bot logic
│   ├── indexer.py          # On-chain event poller
│   ├── main.py             # FastAPI entry point
│   ├── middleware.py       # Security, CORS, and limits middleware
│   ├── oidc.py             # GitHub OIDC integration
│   ├── worker.py           # Background indexer task
│   └── supabase_migration.py # Supabase/Postgres setup
├── dashboard/              # Next.js Frontend (App Router)
├── supabase/               # Database RLS policies
├── tests/                  # Modular Pytest test suite
├── escrow.algo             # Main Smart Contract (Puya/pyTEAL)
├── v0-v7-*.md              # Design Documents (READ THESE FIRST)
└── CONTRACTOR-BRIEF.md      # High-level implementation roadmap
```

---

## 3. Tech Stack & Key Libraries

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, Pydantic, `py-algorand-sdk`.
- **Frontend**: Next.js, TypeScript, Tailwind CSS.
- **Database**: PostgreSQL (Supabase), Alembic for migrations.
- **Testing**: `pytest`, `pytest-asyncio`.
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
Use `pytest` with `pytest-asyncio` for asynchronous tests. Ensure `PYTHONPATH` is set to the root directory:
```bash
PYTHONPATH=. python -m pytest tests/
```
- We have transitioned from monolithic tests (like `test_gateway.py`) to modular suites (e.g., `tests/test_misc_routers.py`, `tests/test_bounty_lifecycle_extended.py`) to prevent environment collisions.
- In CI workflows, `TESTING="True"` is strictly required to bypass rate limits and enable test-specific mocks.
- To mock `Config` properties (like `ALGORAND_NETWORK`) in unit tests, use `PropertyMock` on `gateway.config.Config.<PROPERTY_NAME>`.

### Working with the Database
- The primary DB is Supabase. If `SUPABASE_URL` is missing, it falls back to `algobounty.db` (SQLite).
- Use Alembic for migrations: `alembic -c gateway/alembic.ini upgrade head`.
- Check `gateway/supabase_migration.py` for the canonical SQLAlchemy models.
- RLS policies are located in `supabase/rls_policies.sql`.

### Configuration & Secrets
- All secrets and configuration are centralized in `gateway/config.py`.
- In production, ensure `SECRET_KEY`, `PLATFORM_PRIVATE_KEY`, and `GITHUB_TOKEN` are provided via environment variables or a configured secret manager.

### Smart Contract Integration (`escrow.algo`)
- **State Management**: The contract state machine utilizes Global Boxes (e.g., `_K_STATE`) rather than per-user Local State, ensuring status is universally shared across all participants. A dedicated `_K_INITIALIZED` box prevents re-initialization attacks.
- **Fund Transfers**: All fund transfers (payouts, refunds, splits) are executed securely via Algorand Inner Transactions (`itxn`), replacing older reliance on external transaction grouping or off-chain logging.
- **Fees**: The contract supports fee collection by calculating and sending a 2% fee to a Treasury Account (passed during bounty creation) upon successful payouts.
- **Mediator Validation**: Dispute resolution requires cryptographic verification of a mediator signature using `op.ed25519verify` against an address stored during bounty creation.
- **Integration**: The ABI signature for bounty creation is strictly `(bytes,uint64,uint64,uint64,uint64,address,address)`.

### Security & Authentication Rules
- **Mock Signatures**: The backend restricts mock signatures (e.g., `-MOCK_SIG`) or bypassed `signed_txn` payloads strictly to local environments where `ALGORAND_NETWORK` is set to `sandbox`. On `testnet` or `mainnet`, strict signature verification and payload transmission are enforced.
- **Secret Keys**: `SECRET_KEY` and `GITHUB_TOKEN` are mandatory for `testnet` and `mainnet`. The app will intentionally crash on startup if these are missing.
- **Middleware Integration**: Custom middleware (e.g., `GitHubWebhookSignatureMiddleware`) inherits from `starlette.middleware.base.BaseHTTPMiddleware` and correctly reads the raw request body to validate HMAC signatures.

### Deployment & Operational Notes
- **Background Worker**: The indexer worker (`gateway/worker.py`) deployed via Cloud Run must be configured with flags `--no-cpu-throttling`, `--min-instances 1`, and `--max-instances 1` to ensure continuous execution without downscaling.
- **Database Engine**: In `gateway/database.py`, `connect_args={"check_same_thread": False}` is strictly reserved for SQLite. For PostgreSQL, the engine strictly requires `postgresql+asyncpg://`.
- **Secrets Naming**: GCP Secret Manager secrets mapped in GitHub Actions use hyphens instead of underscores (e.g., `algobounty-jwt-secret`, `algobounty-github-webhook-secret`).

### Frontend Hooks
- `useWallet`: Manages connection to Pera, Defly, and Edge wallets.
- `useEvents`: Subscribes to `/api/v1/events` SSE and triggers callbacks for real-time updates.
- **HITM Mode**: When `is_hitm=True`, the contract sets a `review_deadline`. If the creator doesn't act, the `indexer_polling_task` detects the `auto_released_hitm` log and updates the DB.
- **Karma System (v2)**: Karma changes are applied both in `gateway/routers/bounties.py` (for API-driven actions) and `gateway/main.py` (for on-chain timeouts/logs).

---

## 5. Design Documents Reference

Before implementing features, consult the corresponding design document:
- **v1**: TEAL Escrow Contract spec.
- **v2**: Karma/Reputation System.
- **v4**: Dashboard & API spec.
- **v5**: GitHub Integration (The Bridge).
- **v6**: Human-in-the-Middle (HITM) Mode.

---

## 6. Coding Conventions

- **Python**: Follow PEP 8. Use type hints. Use `ruff` for linting.
- **Frontend**: Use functional components and hooks. Follow the Next.js App Router conventions.
- **Security**: Never hardcode secrets. Use environment variables. Verify all blockchain interactions.
- **UX Audits & Simulations**: When executing proxy user experience tests, always run actual Playwright scripts against the running dashboard and gateway services to capture real screenshots. Generating synthetic mockup images using AI image generation tools (e.g. `generate_image`, Stable Diffusion, Flux, or DALL-E) is strictly forbidden.

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

*Keep this document updated as the project evolves.*
