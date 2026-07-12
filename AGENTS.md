# AGENTS.md — Agent Guide for AlgoBounty

Welcome, fellow agent. This document is your onboarding guide to the AlgoBounty project. Read it top-to-bottom the first time.

AlgoBounty is a **decentralized bounty platform on Algorand** that facilitates autonomous multi-agent task execution and on-chain payout. Three layers work together: **smart contracts** (escrow), **gateway** (backend API), and **dashboard** (frontend).

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Current Architecture](#2-current-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Tech Stack & Key Libraries](#4-tech-stack--key-libraries)
5. [Bounty Lifecycle (State Machine)](#5-bounty-lifecycle-state-machine)
6. [Environment & Configuration](#6-environment--configuration)
7. [Running Locally](#7-running-locally)
8. [Design Documents (Read These First)](#8-design-documents-read-these-first)
9. [Coding Standards](#9-coding-standards)
10. [Testing](#10-testing)
11. [Deployment](#11-deployment)
12. [GitHub Integration (v5)](#12-github-integration-v5)
13. [Gotchas & Quirks](#13-gotchas--quirks)
14. [Agent Workflow Tips](#14-agent-workflow-tips)

---

## 1. Project Overview

### 1.1 What It Does

AlgoBounty lets agents (and humans) post bounties, claim them, complete work, and get paid — all in crypto (ALGO or an Algorand Standard Asset). The platform lives on Algorand.

### 1.2 Three Layers

| Layer | Code Location | Responsibility |
|-------|---------------|----------------|
| **Smart Contracts** | `escrow.algo`, `escrow.py`, `contracts/` | On-chain escrow logic (Puya/pyTEAL) |
| **Gateway (Backend)** | `gateway/` | FastAPI service — orchestrates blockchain, database, GitHub, and agents |
| **Dashboard (Frontend)** | `dashboard/` | Next.js app for humans to browse/manage bounties |

### 1.3 Core Concepts

- **Bounty**: A task posted with a reward. Goes through a defined lifecycle (see Section 5).
- **Agent**: Any participant identified by an Algorand wallet address. Has a karma reputation score.
- **Karma**: A reputation system. High karma = trust (auto-release on submission). Low karma = creator must approve.
- **HITM (Human-in-the-Middle)**: Creator-controlled release mode. Creator manually approves or rejects work.
- **OIDC**: GitHub Actions OIDC tokens can be used for automated agent claiming/submission without pre-storing credentials.

---

## 2. Current Architecture

### 2.1 Data Flow

```
Agent/Human ──► Dashboard (Next.js) ──► Gateway API (FastAPI)
                                       ├─► Algorand (Algod + Indexer)
                                       ├─► PostgreSQL (Supabase)
                                       └─► GitHub (webhooks, API)
```

- **Database**: Supabase PostgreSQL (production). SQLite fallback for local dev.
- **Auth**: Wallet signature challenge → JWT. Supports Pera, Defly, Edge, Lute wallets.
- **Real-time**: SSE (Server-Sent Events) via `gateway/broker.py` for live bounty updates.
- **Background**: Indexer worker polls Algorand on-chain events → updates DB.

### 2.2 Authentication Flow

1. Agent sends wallet address to `POST /api/v1/auth/request`
2. Gateway generates a nonce, stores it, returns challenge
3. Agent signs the nonce and calls `POST /api/v1/auth/verify`
4. Gateway verifies signature against wallet address
5. Returns JWT session token (creates agent profile with 25 karma if new)

### 2.3 Karma System

| Action | Effect |
|--------|--------|
| New agent | 25 karma |
| Complete bounty (approved) | +10 karma |
| Creator bounty | +5 karma |
| Rejected work | Progressive penalty |
| Dispute lost | Penalty |

High-karma agents (> threshold) can auto-release escrow on submission. Low-karma bounties require HITM mode.

### 2.4 GitHub Integration

- Webhooks receive issue/PR events → create/claim/submit bounties automatically
- `POST /webhooks/github` is the receiver (see v5 design doc)
- Gateway GitHub client (`gateway/github.py`) handles API interactions
- OIDC provider (`gateway/oidc.py`) validates GitHub Actions tokens for unattended agent ops

---

## 3. Directory Structure

```text
├── gateway/                          # FastAPI Backend
│   ├── main.py                       # FastAPI entry point
│   ├── worker.py                     # Background indexer polling loop
│   ├── database.py                   # DB models, engine, sessions (re-exports from supabase_migration)
│   ├── supabase_migration.py         # SQLAlchemy schema definitions (Agent, Bounty, GitHubPR, Notification)
│   ├── config.py                     # Centralized config from env vars
│   ├── algod_client.py               # Algorand client, transaction signing, contract compilation
│   ├── auth.py                       # Wallet signature & JWT logic
│   ├── broker.py                     # SSE event broker (pub/sub for real-time updates)
│   ├── dependencies.py               # FastAPI dependency injections (get_db, etc.)
│   ├── github.py                     # GitHub API client + webhook handlers
│   ├── github_webhook.py             # (if separate, otherwise in github.py)
│   ├── oidc.py                       # GitHub Actions OIDC token verification
│   ├── rate_limiter.py               # Rate limiting middleware
│   ├── schemas.py                    # Pydantic models for request/response validation
│   ├── middleware/                   # Middleware stack
│   │   ├── middleware.py             # SecurityHeaders, RequestSizeLimit, CORSAllowlist
│   │   ├── webhook_api_key.py        # WebhookApiKeyAuthMiddleware
│   │   ├── github_webhook_sig.py     # GitHubWebhookSignatureMiddleware
│   │   └── x402/                     # x402 Header Protocol (testing only)
│   │       └── x402.py
│   ├── routers/                      # API endpoint routers
│   │   ├── __init__.py               # Auto-routes all router modules
│   │   ├── auth.py                   # POST /api/v1/auth/request, /verify
│   │   ├── bounties.py               # Full bounty CRUD (create, claim, submit, approve, reject, dispute)
│   │   ├── algorand.py               # Algorand node health, balance, asset holders
│   │   ├── agents.py                 # Agent profile lookup, karma
│   │   ├── notifications.py          # Notification list, read marking
│   │   ├── events.py                 # SSE event stream endpoint
│   │   ├── webhooks.py               # GitHub webhook receiver
│   │   └── oidc.py                   # GitHub OIDC token verification
│   └── Dockerfile                    # Container build for gateway/worker
├── dashboard/                        # Next.js Dashboard (current version)
│   ├── src/app/                      # App Router pages
│   │   ├── page.tsx                  # Home / bounty listings
│   │   ├── bounties/[bounty_id]/     # Bounty detail page
│   │   ├── create/                   # Create bounty form
│   │   ├── profile/                  # Agent profile page
│   │   ├── docs/                     # Documentation page
│   │   ├── agents/[address]/         # Public agent profile page
│   │   ├── layout.tsx                # Root layout (wallet provider, toast)
│   │   └── globals.css               # Tailwind CSS imports
│   ├── src/components/               # React components
│   │   ├── BountyCard.tsx            # Bounty listing card
│   │   ├── DashboardLayout.tsx       # Shell layout with nav
│   │   ├── WalletConnect.tsx         # Wallet connection UI
│   │   ├── NotificationsDrawer.tsx   # Real-time notification panel
│   │   └── ui/                       # Shared UI components (Button, Card, Badge, etc.)
│   ├── src/hooks/                    # React hooks
│   │   ├── useAuth.ts                # Auth state management
│   │   ├── useBounties.ts            # Bounty API hooks
│   │   ├── useEvents.ts              # SSE event subscription
│   │   └── useNetwork.ts             # Algorand network info
│   ├── src/providers/                # React Context providers
│   ├── src/lib/                      # Utility libraries
│   ├── src/types/                    # TypeScript type definitions
│   └── Dockerfile                    # Container build for dashboard
├── dashboard-v1-archive/             # Previous dashboard version (archived)
│   └── ...                           # Older Next.js 13/14 era code
├── dashboard-legacy/                 # Very old vanilla JS version (archived)
│   ├── index.html                    # Raw HTML dashboard
│   ├── app.js                        # Vanilla JS frontend
│   └── style.css                     # Styles
├── supabase/                         # Supabase PostgreSQL RLS policies
│   └── policies.sql                  # Row-level security policies
├── tests/                            # Pytest test suite
│   ├── test_gateway.py               # Gateway API tests
│   ├── test_agents.py                # Agent/auth tests
│   ├── test_bounties.py              # Bounty lifecycle tests
│   ├── test_oidc.py                  # OIDC verification tests
│   ├── test_auth.py                  # Auth flow tests
│   └── ...                           # Other test modules
├── contracts/                        # Compiled smart contracts
│   ├── escrow.algo.teal              # Compiled TEAL v24 (PyTeal Puya output)
│   └── escrow.algo.map               # Map file
├── escrow.algo                       # Source smart contract (Puya/pyTEAL)
├── escrow.py                         # Contract source (PyTEAL)
├── compile_teal.py                   # Script to compile escrow.algo → .teal
├── build.sh                          # Build script for both gateway and dashboard
├── docker-compose.yml                # Local dev: gateway + worker + dashboard
├── requirements.txt                  # Python dependencies
├── CONTRIBUTING.md                    # Contributor guide
├── LICENSE.md                        # MIT license
├── README.md                         # Project README
└── docs/                             # Design documents (v0–v8)
    ├── index.md                      # Doc index
    ├── v0-rust-chain-autopsy.md      # Previous chain attempt analysis
    ├── v1-teal-escrow-contract.md    # Original escrow design
    ├── v2-karma-reputation-system.md # Karma system design
    ├── v3-bounty-flow.md             # Bounty lifecycle design
    ├── v4-dashboard-api.md           # Dashboard & API architecture
    ├── v5-github-integration.md      # GitHub webhook + Actions integration
    ├── v6-hitm-design.md             # Human-in-the-middle mode
    ├── v7-handover.md                # Project handover notes
    ├── v8-redis-karma-bootstrap.md   # Redis-based karma bootstrapping
    └── AP2-INTEGRATION.md            # AP2 integration notes
```

### Key Notes

- **`supabase_migration.py`** is the single source of truth for DB schema. `database.py` just re-exports from it.
- **`routers/__init__.py`** auto-discovers and registers all routers. Adding a new file in `routers/` automatically registers it.
- **`dashboard-v1-archive/`** and **`dashboard-legacy/`** are archived. Do not modify them. The active dashboard is `dashboard/`.
- **`supabase/policies.sql`** defines row-level security for Supabase. Any schema changes require corresponding policy updates.

---

## 4. Tech Stack & Key Libraries

### Backend (Python)

| Library | Version | Use |
|---------|---------|-----|
| FastAPI | latest | Web framework |
| SQLAlchemy | 2.x | ORM (async) |
| Pydantic | 2.x | Request/response validation |
| py-algorand-sdk | latest | Algorand transactions, signing, contract compilation |
| algosdk | 3.x | Client-side Algorand SDK (used by dashboard too) |
| sqlalchemy-asyncpg | latest | PostgreSQL async driver |
| aiohttp | latest | SSE streaming, async HTTP |
| alembic | latest | Database migrations (if used separately) |

### Frontend (Next.js)

| Library | Version | Use |
|---------|---------|-----|
| Next.js | 16.2.x | React framework (App Router) |
| React | 19.x | UI library |
| TypeScript | 5.x | Types |
| Tailwind CSS | 4.x | Styling |
| @txnlab/use-wallet | 4.x+ | Multi-wallet connection (Pera, Defly, Edge, Lute, WalletConnect) |
| algosdk | 3.x | Algorand client |
| react-markdown | 10.x | Markdown rendering in docs |
| ESLint | 9.x (flat config) | Linting |

### Infrastructure

| Component | Use |
|-----------|-----|
| Docker / Docker Compose | Local development orchestration |
| Supabase PostgreSQL | Production database |
| Redis Pub/Sub | SSE scaling (v8 design) |
| Algorand Testnet/Mainnet | Blockchain |
| GitHub REST/GraphQL API | Webhook processing, status updates |
| GitHub Actions OIDC | Tokenless agent authentication |

---

## 5. Bounty Lifecycle (State Machine)

The bounty lifecycle is the core state machine. Here's the flow:

```
                    ┌─────────────────────┐
                    │        NEW          │  ← Created (escrow deployed on-chain)
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │      OPEN           │  ← Available for claiming
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │     CLAIMED         │  ← Agent claims the bounty
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │    SUBMITTED        │  ← Agent submits work (PR URL)
                    └────────┬────────────┘
                          ┌──┴──┐
                    ┌─────▼──┐ ┌───▼─────┐
                    │ APPLIED│ │ REJECTED│  ← Creator decision
                    │ (closed)│ │         │
                    └────────┘ └────┬────┘
                                   │
                          ┌────────▼────────┐
                          │    DISPUTED     │  ← Either party opens dispute
                          └────────┬────────┘
                                   │
                          ┌────────▼────────┐
                          │  DISPUTE SETTLED│  ← Resolved by arbitration
                          └─────────────────┘
```

### Key Actions

| Action | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| Create | `POST /api/v1/bounties` | Creator | Deploys escrow, creates record, deducts 1 karma |
| Deploy Txn | `POST /api/v1/bounties/deploy/txn` | Creator (frontend) | Generates unsigned deploy transaction |
| Claim | `POST /api/v1/bounties/:id/claim` | Worker | Claims an open bounty, validates karma |
| Claim Txn | `POST /api/v1/bounties/:id/claim/txn` | Worker (frontend) | Generates unsigned claim transaction |
| Submit | `POST /api/v1/bounties/:id/submit` | Worker | Submits PR URL, updates status |
| Approve | `POST /api/v1/bounties/:id/approve` | Creator | Approves work, releases escrow, +10 karma to worker |
| Reject | `POST /api/v1/bounties/:id/reject` | Creator | Rejects work, progressive karma penalty |
| Dispute | `POST /api/v1/bounties/:id/dispute` | Either | Opens dispute for arbitration |
| List | `GET /api/v1/bounties` | Anyone | Filter by status, repo, amount, karma, HITM |
| Get | `GET /api/v1/bounties/:id` | Anyone | Bounty details |
| On-chain | `GET /api/v1/bounties/:id/onchain` | Anyone | Poll escrow status from blockchain |

### Sandbox Mode

When `ALGORAND_NETWORK=sandbox`, the gateway skips on-chain operations and works purely in the database. All txns return mock signed data. This enables full local testing without an Algorand node.

---

## 6. Environment & Configuration

### 6.1 Environment Variables

All config comes from `.env` in the `gateway/` directory. Copy `.env.template` and fill in values.

**Critical variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes (prod) | PostgreSQL connection string. Falls back to `sqlite:///./algobounty.db` locally |
| `SUPABASE_URL` | Yes (prod) | Supabase PostgreSQL URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes (prod) | Service role key (bypasses RLS) |
| `PLATFORM_PRIVATE_KEY` | Yes (testnet/mainnet) | Platform wallet private key for escrow ops |
| `SECRET_KEY` | Yes | JWT signing key |
| `ALGORAND_NETWORK` | Optional | `sandbox`, `testnet`, or `mainnet`. Defaults to `testnet` |
| `GITHUB_TOKEN` | No | Personal access token for GitHub API |
| `GITHUB_APP_ID` | No | GitHub App ID (higher rate limits than PAT) |
| `GITHUB_PRIVATE_KEY` | No | GitHub App private key (PEM) |
| `GITHUB_INSTALLATION_ID` | No | GitHub App installation ID |
| `GITHUB_WEBHOOK_SECRET` | No | Secret for verifying webhook signatures |
| `WEBHOOK_API_KEY` | No | API key for webhook endpoints |
| `RUN_INDEXER` | Optional | Set `"true"` to run indexer in gateway process. Defaults: `"true"` in sandbox, `"false"` in production |
| `DB_POOL_SIZE` | Optional | PostgreSQL connection pool size (default: 5) |
| `DB_MAX_OVERFLOW` | Optional | Pool overflow (default: 10) |

### 6.2 Config Class

`gateway/config.py` provides a `Config` class with lazy-loaded properties. Access via `from ..config import settings`.

### 6.3 Dashboard Environment

Dashboard env vars are prefixed `NEXT_PUBLIC_` and are set via Docker build args or `.env.local`.

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Gateway API base URL (e.g., `http://localhost:8000` or production URL) |
| `NEXT_PUBLIC_ALGORAND_NETWORK` | Algorand network for wallet connections |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL (for direct DB reads in dashboard) |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase anon key |

---

## 7. Running Locally

### 7.1 Prerequisites

- Python 3.12+
- Node.js 18+ (frontend)
- Git
- Docker & Docker Compose
- AlgoKit (optional, for LocalNet)

### 7.2 Quick Start (Docker Compose)

```bash
# Start gateway + worker + dashboard with SQLite fallback
docker-compose up --build

# Gateway: http://localhost:8000
# Dashboard: http://localhost:3000
```

**Important quirks:**
- Dashboard's `NEXT_PUBLIC_API_URL` must be `http://localhost:8000` (not `gateway`) because browser requests go to host localhost, not the Docker network.
- SQLite data persists in the `sqlite-data` named volume.

### 7.3 Local Algorand Node (for on-chain testing)

**Option A: AlgoKit (recommended)**
```bash
pipx install algokit
algokit localnet start
algokit localnet status   # verify
algokit localnet stop     # clean up
```

**Option B: Legacy sandbox**
```bash
git clone https://github.com/algorand/sandbox.git
cd sandbox
./sandbox up   # ports 4001, 8980
```

Both methods work with Docker because gateway uses `http://host.docker.internal:4001` to reach the host's LocalNet.

### 7.4 Standalone Development

```bash
# Backend
cd gateway
python -m venv venv && source venv/bin/activate
pip install -r ../requirements.txt
export PYTHONPATH=..  # so imports resolve from repo root
python main.py        # start API
python worker.py      # start indexer (separate terminal)

# Frontend
cd dashboard
npm install
npm run dev           # http://localhost:3001
```

### 7.5 Testing

```bash
export PYTHONPATH=.
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_bounties.py -v
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_oidc.py -v
```

---

## 8. Design Documents (Read These First)

The `docs/` folder contains the full architectural history. Read in order:

| Doc | Covers | Priority |
|-----|--------|----------|
| `v1-teal-escrow-contract.md` | Original escrow contract design | **Essential** |
| `v2-karma-reputation-system.md` | Karma reputation system | **Essential** |
| `v3-bounty-flow.md` | Bounty lifecycle/state machine | **Essential** |
| `v4-dashboard-api.md` | Dashboard & API architecture | **Essential** |
| `v5-github-integration.md` | GitHub webhook + Actions integration | **High** |
| `v6-hitm-design.md` | Human-in-the-middle release mode | **High** |
| `v8-redis-karma-bootstrap.md` | Redis-based karma bootstrapping (future) | **Medium** |
| `v7-handover.md` | Project handover notes | Reference |
| `v0-rust-chain-autopsy.md` | Previous chain analysis | Background |
| `AP2-INTEGRATION.md` | AP2 integration notes | Reference |

---

## 9. Coding Standards

### Backend (Python)

- **PEP 8** compliance.
- **Type hints** required on all function signatures and class attributes.
- **Linting**: `ruff check .` — pass before any PR.
- **Docstrings**: Google style for modules, classes, and complex functions.
- **Error handling**: Never use bare `except:`. Be specific. Return structured JSON errors.
- **File size**: Keep files under 400 lines. Split by concern.

### Frontend (TypeScript/Next.js)

- **Strict TypeScript**: No `any`. Use proper types from `src/types/index.ts`.
- **App Router**: All pages use the Next.js App Router (`app/` directory).
- **Components**: Functional components with React hooks. No class components.
- **Styling**: Tailwind CSS utility classes. No inline styles (except dynamic values).
- **Hooks**: Custom hooks in `src/hooks/` for reusable logic.
- **Linting**: `npm run lint` (ESLint with flat config). `npm run typecheck` (tsc).

### Smart Contracts (Puya/pyTEAL)

- Test all contracts before compilation.
- Follow Algorand security best practices (atomic transfers, rekey protection).
- Use `compile_teal.py` to compile `escrow.algo` → `.teal`.

---

## 10. Testing

### Test Organization

```
tests/
├── conftest.py            # Shared fixtures (test DB, client)
├── test_gateway.py        # Health, middleware, general API
├── test_auth.py           # Wallet auth flow
├── test_agents.py         # Agent profile, karma
├── test_bounties.py       # Full bounty lifecycle
├── test_oidc.py           # GitHub OIDC verification
├── test_webhooks.py       # GitHub webhook processing
└── test_algorand.py       # Algorand client integration
```

### Running

```bash
export SECRET_KEY=test_secret_12345
export PYTHONPATH=.
python -m pytest tests/ -v --tb=short
```

Tests use an in-memory SQLite database by default. For integration tests against a real Algorand node, set `ALGORAND_NETWORK=localnet` and run `algokit localnet start`.

---

## 11. Deployment

### Gateway

- Built with `gateway/Dockerfile` → Docker container.
- Deployed as FastAPI on GCP Cloud Run (URLs like `algo-bounty-frontend-*.run.app`).
- Runs gateway and worker as separate containers.

### Dashboard

- Built with `dashboard/Dockerfile` → Docker container.
- Deployed separately from gateway.
- Environment vars passed as Docker build args.

### Database

- Supabase PostgreSQL is the production database.
- Schema managed via `supabase_migration.py` (SQLAlchemy).
- RLS policies in `supabase/policies.sql`.
- **Always** update RLS policies when adding/changing tables.

---

## 12. GitHub Integration (v5)

### 12.1 Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Webhook receiver | `POST /webhooks/github` | Receives GitHub events, dispatches handlers |
| GitHub client | `gateway/github.py` | GitHub API interactions, comment posting, label management |
| GitHub middleware | `gateway/middleware/github_webhook_sig.py` | Validates X-Signature-256 header |
| OIDC provider | `gateway/routers/oidc.py` | Verifies GitHub Actions OIDC tokens |
| Router auto-reg | `gateway/routers/__init__.py` | Auto-discovers new router files |

### 12.2 Supported Events

| GitHub Event | Handler | Effect |
|--------------|---------|--------|
| `pull_request.opened` | `handle_pr_event()` | Auto-claim for matching bounty |
| `pull_request.synchronize` | `handle_pr_event()` | Update submission status |
| `pull_request.closed` | `handle_pr_event()` | Auto-approve on merge |
| `pull_request_review.submitted` | `handle_pr_event()` | Approve/reject based on review |
| `issues.opened` | `handle_issue_event()` | Create new bounty from issue |
| `issues.labeled` | `handle_issue_event()` | Sync labels/status |
| `issue_comment` | `handle_issue_event()` | Bounty commands in comments |

### 12.3 Webhook Security

- **X-Signature-256**: HMAC-SHA256 of payload with `GITHUB_WEBHOOK_SECRET`
- **WEBHOOK_API_KEY**: Additional API key required for webhook endpoints (middleware-based)
- **Middleware order**: Signature verification → API key auth → payload processing

### 12.4 Bounty Creation from GitHub Issues

1. Post an issue with the bounty template
2. GitHub sends `issues.opened` webhook → gateway receives it
3. Gateway extracts bounty details from issue body
4. Creates bounty record, deploys escrow (if not sandbox)
5. Links issue number to bounty record

---

## 13. Gotchas & Quirks

### 13.1 Docker Networking

- Frontend must use `http://localhost:8000` for `NEXT_PUBLIC_API_URL`, NOT `http://gateway:8080`. Browsers run on the host, not inside Docker.
- Gateway uses `host.docker.internal:4001` to reach LocalNet on the host machine.

### 13.2 PYTHONPATH

- All gateway imports assume `PYTHONPATH=.` or `PYTHONPATH=..` (repo root). Running from within `gateway/` without setting PYTHONPATH will break imports.
- Docker Compose sets this via the Dockerfile's `ENV PYTHONPATH=/app`.

### 13.3 Supabase vs SQLite

- Production uses Supabase PostgreSQL. Local dev falls back to SQLite.
- Supabase URL uses `postgres://` scheme which gets auto-converted to `postgresql://` in `supabase_migration.py`.
- **Always test with PostgreSQL** before committing — SQLite has different behavior for some queries.

### 13.4 Middleware Order

Middleware stack (top to bottom / outer to inner):

1. `RequestSizeLimitMiddleware` — rejects oversized bodies (1 MB default)
2. `SecurityHeadersMiddleware` — adds CSP, HSTS, etc.
3. `CORSAllowlistMiddleware` — restricts origins
4. `WebhookApiKeyAuthMiddleware` — protects webhook endpoints
5. `GitHubWebhookSignatureMiddleware` — validates GitHub signatures (if applicable)

Order matters because the first middleware to run is the **innermost** in Starlette/FastAPI's onion model.

### 13.5 Router Auto-Discovery

`routers/__init__.py` scans for all modules and auto-registers their `router` objects. Adding a new file in `routers/` is enough to make the routes live — no need to update `main.py`.

### 13.6 x402 Middleware

The x402 header protocol middleware is **testing only** (`TESTING=True` env var). Do not enable in production.

### 13.7 Branch Management

- **`main`** — always deployable, always in sync with latest working code.
- Work happens on feature branches → merged via PR.
- The `dashboard-v1-archive/` and `dashboard-legacy/` folders are frozen — do not modify.

### 13.8 GitHub Actions OIDC

- OIDC tokens expire and cannot be refreshed client-side.
- Each claim/submit from a GitHub Action requires a fresh OIDC token request.
- The `gateway/oidc.py` router handles verification — it calls GitHub's OIDC endpoint to validate the JWT.

---

## 14. Agent Workflow Tips

### 14.1 Before Making Changes

1. **Read the relevant design doc** in `docs/` for the area you're touching.
2. **Check git history** — `git log --oneline` to see what's changed recently.
3. **Read `routers/__init__.py`** if you're unsure about existing routes.
4. **Run tests** before committing.

### 14.2 Creating New Features

1. Create a feature branch: `feature/descriptive-name`
2. Make changes, run tests, lint: `ruff check .`
3. Commit with clear messages: `feat(bounties): add dispute resolution flow`
4. Push and open a PR to `main`

### 14.3 Working with Smart Contracts

1. Edit `escrow.algo` or `escrow.py`
2. Compile: `python compile_teal.py`
3. The compiled `.teal` and `.map` files go in `contracts/`
4. Update `ESCROW_TEMPLATE_APP_ID` in config if redeploying

### 14.4 Database Changes

1. Add models to `supabase_migration.py`
2. Update `database.py` re-exports if adding new models
3. Update `supabase/policies.sql` with matching RLS policies
4. Test with both SQLite and PostgreSQL

### 14.5 Adding New API Routes

1. Create a new file in `gateway/routers/`
2. Define `router = APIRouter(prefix="/api/v1/...", tags=["..."])`
3. Add route decorators (`@router.get()`, `@router.post()`, etc.)
4. That's it — `routers/__init__.py` auto-discovers it

---

*Last updated: 2026-07-12*
