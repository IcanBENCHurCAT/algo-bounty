# AlgoBounty — Contractor/Agent Brief

**This is the handoff document for contractors and agents who will implement AlgoBounty.**

Read everything in order. This document tells you exactly what's been done, what's needed, and how to proceed.

---

## What You're Building

AlgoBounty is an **agent-to-agent bounty platform on Algorand**. Think of it like GitHub Sponsors or Upwork, but built for AI agents with:

- **On-chain escrow** — bounties paid in ALGO or any Algorand Standard Asset (ASA)
- **Reputation system** — karma scoring for both creators and workers
- **Human-in-the-middle option** — creators can require human review before payment release
- **GitHub integration** — bounties tied to GitHub issues/PRs, with automated notifications
- **Dashboard & API** — public-facing marketplace for browsing and claiming bounties

---

## What's Already Done (Your Starting Point)

### 1. Design Documents ✅ (7 files at repo root)

All design docs are at the **repo root** (not in a subdirectory):

| Doc | File | Status |
|-----|------|--------|
| v0 — Rust Chain Autopsy | `v0-rust-chain-autopsy.md` | ✅ Done (forensic analysis of prior project failures) |
| v1 — TEAL Escrow Contract | `v1-teal-escrow-contract.md` | ✅ Done (full spec for on-chain escrow) |
| v2 — Karma/Reputation System | `v2-karma-reputation-system.md` | ✅ Done (scoring, newbie protection, decay) |
| v3 — Verification/Challenge | (covered in v0/v2 docs) | ✅ Done (wallet signature auth, no opaque challenges) |
| v4 — Dashboard & API | `v4-dashboard-api.md` | ✅ Done (REST API spec, UI wireframes) |
| v5 — GitHub Integration | `v5-github-integration.md` | ✅ Done (webhook handler, issue/PR flow) |
| v6 — HITM Mode | `v6-hitm-design.md` | ✅ Done (human review layer with dispute resolution) |
| v7 — Project Handover | `v7-handover.md` | ✅ Done (this overview doc) |

> **Note:** v3 is not a standalone file. Its content (verification via wallet signatures instead of opaque challenges) is covered within v0 (Rust Chain Autopsy) and v2 (Karma/Reputation). The CONTRACTOR-BRIEF v7 handover doc also confirms this.

### 2. Smart Contract ✅

`escrow.algo` (748 lines, Puya/pyTEAL) — **working code, not just a spec.**

It includes:
- Create bounty with escrow (ALGO or ASA)
- Claim bounty by worker
- Submit proof of work
- Approve/reject work
- Dispute with resolution
- Auto-release on timeout
- Auto-refund if creator abandons
- 2.5% platform fee at payout
- GitHub OIDC bridge support
- Claim timeout (48h)
- Dispute timeout (30d)
- Box storage utilities
- State machine with all transitions

### 3. Backend — Gateway (FastAPI) ✅

`gateway/main.py` (768 lines) — Full REST API with **32+ endpoints**:

| Module | File | Status |
|--------|------|--------|
| Main API | `gateway/main.py` | ✅ ~768 lines, 32 endpoints |
| Auth | `gateway/auth.py` | ✅ Wallet signature + JWT (AlgSDK verify) |
| DB Models | `gateway/database.py` | ✅ Re-exports from supabase_migration |
| Supabase/Postgres | `gateway/supabase_migration.py` | ✅ Full DDL, models, engine, Alembic |
| Algorand Client | `gateway/algod_client.py` | ✅ Health check, balance, holders, compile |
| GitHub Webhooks | `gateway/github.py` | ✅ HMAC verification, issue/PR handlers |
| Rate Limiting | `gateway/rate_limiter.py` | ✅ Middleware with config |
| Security Middleware | `gateway/middleware.py` | ✅ Headers, CORS, size limits |
| Indexer | `gateway/indexer.py` | ✅ Polls on-chain events, syncs to DB |
| SSE Broker | EventBroker in main.py | ✅ Real-time event stream for dashboard |

**Key endpoints:**
- `POST /auth/request` / `POST /auth/verify` — Wallet signature auth flow
- `GET /bounties` / `GET /bounties/{id}` / `POST /bounties` — CRUD
- `POST /bounties/{id}/claim` / `POST /bounties/{id}/submit` / `POST /bounties/{id}/approve` / `POST /bounties/{id}/reject` / `POST /bounties/{id}/dispute` — Bounty lifecycle
- `GET /agents/{address}` / `POST /agents` — Agent profiles
- `GET /notifications` — Notification endpoint
- `GET /stream` — SSE event stream
- `POST /webhooks/github` — GitHub webhook receiver

### 4. Frontend — Dashboard (Next.js) ✅

`dashboard/` (261 lines page, full Next.js App Router):

| Component | Status |
|-----------|--------|
| Next.js App Router pages | ✅ / |
| Dashboard layout | ✅ |
| Bounty card/list | ✅ |
| Wallet connect (Pera) | ✅ Full auth flow with challenge/sign/verify |
| Supabase client helpers | ✅ client, middleware, server |
| API client | ✅ `dashboard/src/lib/api.ts` (296 lines) |
| Toast notifications | ✅ |

### 5. Database ✅

- **PostgreSQL via Supabase** (primary production DB)
- **SQLite** (local dev fallback — only when SUPABASE_URL not set)
- **Alembic** migrations configured (`gateway/alembic.ini` + `gateway/migrations/`)
- **RLS policies** defined in `supabase/rls_policies.sql`
- Tables: `agents`, `bounties`, `github_prs`, `notifications`

### 6. Security Hardening (recent) ✅

- Removed hardcoded JWT secret fallback (now requires env var)
- Fixed database exhaustion via implicit agent registration
- HMAC GitHub webhook signature verification
- Alembic migration for schema management
- Security headers middleware
- Request size limit middleware
- CORS origin allowlist

### 7. CI/CD ✅

- GitHub Actions: CI/CD workflow + unit test workflow
- Dockerfile for containerized deployment
- GCP Cloud Run deployment scripts

---

## What's Still Needed (Implementation Priority)

### Priority 1: Security — Remove Mock Signature Bypass

`gateway/auth.py` still has a `MOCK_SIG` bypass that allows fake signatures in dev:
```python
if signature.endswith("MOCK_SIG"):
    mock_addr = signature.split("-")[0]
    return mock_addr == address
```
**Action:** Remove this entirely. Real wallet signatures only.

### Priority 2: Algorand Integration — Real Chain Interaction

Current state: `algod_client.py` has health check, balance, and asset holders, but:
- No real escrow contract deployment (only compile)
- Bounty creation/claim/approve are DB-only (no on-chain txs)
- No indexer polling loop running in background

**Action:** Integrate PyAlgoSDK for:
- Deploy `escrow.algo` on testnet
- Create claim transactions from gateway
- Monitor indexer for escrow state changes
- Auto-update bounty status from chain

### Priority 3: Frontend — Real Wallet Integration

`dashboard/src/hooks/useWallet.ts` currently:
- Checks for Pera Wallet (`window.PeraWalletConnect`)
- Connects → requests challenge → signs → verifies
- **But:** the actual wallet SDK connection needs proper initialization and error handling
- Dashboard needs to display real escrow status (not just DB state)

**Action:**
- Verify Pera Wallet SDK integration works end-to-end
- Add wallet connect for Defly/Edge wallet too
- Show on-chain bounty status on dashboard
- Fix any connection errors

### Priority 4: GitHub Integration — Webhook Handler

`gateway/github.py` has handlers for issue and PR events, but:
- No actual bot deployment or messaging on GitHub
- `log_bot_comment` is stubbed (just prints/logs)
- No GitHub App/OIDC token management
- No actual PR comment/bounty linking flow

**Action:** Implement the full flow from v5 spec:
- GitHub App creation and installation
- Webhook secret management
- Issue → bounty creation flow
- PR → bounty linking (via `#ALGO-XXXX` pattern)
- Automated comments on PRs/issues

### Priority 5: Smart Contract — Expand & Test

`escrow.algo` is working but needs:
- Full HITM mode testing (v6 spec)
- Karma tracking integration
- Comprehensive test suite (current tests are minimal: `test_escrow_mock.py`)
- Edge case tests (timeouts, disputes, ghosting, etc.)

### Priority 6: Rate Limiting — Activate

`gateway/rate_limiter.py` exists but may not be fully activated on all endpoints.
Verify and configure appropriate rate limits per endpoint tier.

### Priority 7: Indexer Background Task

`gateway/indexer.py` has polling functions but no background scheduler.
- Set up a periodic task (Celery/APScheduler) to call `poll_bounty_events()`
- Sync chain state to DB for dashboard display

### Priority 8: Secrets Management

- `SECRET_KEY` in `gateway/auth.py` reads from env — good
- GitHub webhook secret needs secure storage (env var or Secret Manager)
- Algorand node credentials need secure storage

---

## How to Proceed

### 1. Environment Setup

```bash
# Clone the repo
git clone https://github.com/IcanBENCHurCAT/algo-bounty.git
cd algo-bounty

# Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment variables (create gateway/.env)
cp gateway/.env.template gateway/.env
# Edit gateway/.env with:
#   SUPABASE_URL=... (or DATABASE_URL for local SQLite)
#   SECRET_KEY=<random-string>
#   ALGORAND_NODE_URL=... (sandbox or testnet)
#   GITHUB_WEBHOOK_SECRET=... (if testing GitHub integration)
```

### 2. Run the Gateway

```bash
export PYTHONPATH=.
python gateway/main.py
```

Server starts on port 8000. Dashboard is at `http://localhost:8000/dashboard/`.

### 3. Run Tests

```bash
export PYTHONPATH=.
pytest tests/ -v
```

### 4. Database Setup

- **Supabase:** Run `gateway/supabase_migration.py` to see DDL, then paste into Supabase SQL Editor
- **SQLite (local):** Automatically used when SUPABASE_URL is not set

### 5. Frontend Setup

```bash
cd dashboard
npm install
npm run dev
```

Dashboard at `http://localhost:3000`.

---

## Key Technical Details

### The Escrow Contract State Machine

```
OPEN → CLAIMED → SUBMITTED → (DISPUTED → CLOSED)
                          → REJECTED → SUBMITTED (loop for revisions)
                          → CLOSED (approved)
CLAIMED → CLAIM_EXPIRED → OPEN (if worker ghosts)
SUBMITTED → CLOSED (auto-release if review expires)
DISPUTED → DISPUTED_TIMEOUT → CLOSED (50/50 split at 30 days)
```

### The Karma System (v2 spec)

New accounts start with 0 karma (+25 bonus on creation). Karma changes based on:
- Completing a bounty: +5 karma, +2 if approved without dispute
- Ghosting (claim timeout): -20 karma
- Fake/broken work: -3 karma
- Being disputed and losing: -5 karma
- Being disputed and winning: +3 karma
- Creator ghosting (no review): +5 karma to worker, -3 to creator

### File Structure

```
algo-bounty/
├── gateway/                # FastAPI backend
│   ├── main.py             # Main API (32+ endpoints)
│   ├── auth.py             # Wallet signature + JWT
│   ├── database.py         # DB models (re-exports from supabase_migration)
│   ├── supabase_migration.py # DDL, models, Alembic setup
│   ├── algod_client.py     # Algorand client utilities
│   ├── github.py           # GitHub webhook handler
│   ├── rate_limiter.py     # Rate limiting middleware
│   ├── middleware.py        # Security headers, CORS, size limits
│   ├── indexer.py          # On-chain event poller
│   └── migrations/         # Alembic migrations
├── dashboard/              # Next.js frontend (App Router)
│   ├── src/app/            # Pages
│   ├── src/components/     # React components
│   ├── src/hooks/          # useWallet hook
│   ├── src/lib/            # API client, Supabase helpers
│   └── src/utils/supabase/ # Client/middleware/server configs
├── tests/                  # Test suite
├── supabase/               # RLS policies
├── escrow.algo             # Puya/pyTEAL escrow contract (748 lines)
├── v0-v7*.md               # Design documents
├── AGENTS.md               # Agent guide
├── CONTRACTOR-BRIEF.md     # This file
└── README.md               # Project overview
```

---

## Common Questions

**Q: Do I need to rewrite the escrow contract?**
A: No. `escrow.algo` (748 lines) is complete with all major features. Expand tests and integrate it with the gateway.

**Q: Is the database working?**
A: Yes. Supabase PostgreSQL is configured with Alembic. SQLite falls back when SUPABASE_URL is not set.

**Q: How do I test the GitHub integration?**
A: Use `ngrok` or `localtunnel` to expose the webhook endpoint, then configure a GitHub test repo. The HMAC verification is implemented in `gateway/github.py`.

**Q: Can I deploy this to GCP?**
A: Yes. Dockerfile and deploy scripts are ready. Use Cloud Run + Cloud SQL.

---

## What to Do Next

1. **Fix the MOCK_SIG bypass** in `gateway/auth.py` — remove it, real signatures only
2. **Integrate real Algorand chain interaction** — deploy escrow, create/claim via txns
3. **Implement the full GitHub webhook flow** — not just stubs
4. **Expand the test suite** — target 80%+ coverage
5. **Run the indexer background task** — sync chain to DB
6. **End-to-end test** — deploy to testnet, connect wallet, create bounty, claim, approve

---

*This brief is a living document. Update it as you learn more.*
