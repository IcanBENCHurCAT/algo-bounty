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

### Running the Gateway & Worker
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
- Mock signatures are often used in dev (suffix `-MOCK_SIG`). In production-ready code, ensure strict verification.

### Middleware Implementation
- When adding middleware to the Gateway, inherit from `starlette.middleware.base.BaseHTTPMiddleware` to avoid signature mismatches.

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
