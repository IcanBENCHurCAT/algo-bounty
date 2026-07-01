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

### 1. Design Documents ✅

All design docs are in `/home/st9797/.openclaw/workspace/algo-bounty-design/`:

- **v0** — Rust Chain Autopsy (what went wrong in the previous project)
- **v1** — TEAL Escrow Contract (full spec for the on-chain escrow)
- **v2** — Karma/Reputation System (newbie protection, scoring, decay)
- **v3** — Verification/Challenge (wallet signatures only, no opaque challenges)
- **v4** — Dashboard & API (full REST API spec, UI wireframes, deployment)
- **v6** — HITM Mode (human review layer with dispute resolution)
- **v7** — Handover doc (this is it, or in `v7-handover.md`)

### 2. Smart Contract ✅

`escrow.algo` (25KB Puya/pyTEAL) — **This is working code, not just a spec.**

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

### 3. What's Missing

- **v5-github-integration.md** — Not written yet. This is your first priority.
- **v7-governance-economics.md** — Optional, but useful if building a business case.
- **Actual implementation** — The escrow.algo has basic methods but needs:
  - HITM mode methods (from v6 spec)
  - Karma tracking methods (from v2 spec)
  - Full test suite
  - GitHub webhook receiver
  - FastAPI gateway (from v4 spec)
  - Frontend dashboard (from v4 wireframes)

---

## How to Read This Project

### The Escrow Contract (`escrow.algo`)

The escrow contract is the heart of AlgoBounty. It manages:

```
State Machine:
OPEN → CLAIMED → SUBMITTED → (DISPUTED → CLOSED)
                          → REJECTED → SUBMITTED (loop for revisions)
                          → CLOSED (approved)
CLAIMED → CLAIM_EXPIRED → OPEN (if worker ghosts)
SUBMITTED → CLOSED (auto-release if review expires)
DISPUTED → DISPUTED_TIMEOUT → CLOSED (50/50 split at 30 days)
```

Each bounty has:
- `creator` — who posted the bounty
- `worker` — who claimed it
- `escrow_amount` — how much is locked
- `asset_id` — ALGO (0) or ASA
- `state` — current state of the bounty
- `payout_type` — PAYOUT, REFUND, or SPLIT
- `hitm` — whether human review is required
- `review_days` — how long the creator has to review (default 7)

### The Karma System (v2 spec)

New accounts start with:
- 0 karma (but get +25 bonus on creation)
- "Novice" tier status
- Forced HITM mode for first 3 bounties

Karma changes based on:
- Completing a bounty: +5 karma, +2 if approved without dispute
- Ghosting (claim timeout): -20 karma
- Fake/broken work: -3 karma
- Being disputed and losing: -5 karma
- Being disputed and winning: +3 karma
- Creator ghosting (no review): +5 karma to worker, -3 to creator
- 90-day grace period for new accounts (reduced penalties)

### GitHub Integration (v5 — write this one!)

The flow:
1. Creator creates an issue in a repo
2. Bot comments on the issue with a bounty link
3. Creator posts escrow → bounty status updates on GitHub
4. Worker claims bounty → bot comments "bounty claimed"
5. Worker submits PR → bot comments "solution submitted"
6. Creator reviews → approves or rejects via bot
7. If approved → bot comments "bounty approved, payment released"
8. If rejected → bot comments "changes requested"

PRs reference bounties with `#ALGO-XXXX` pattern.

---

## Your First Tasks

### Priority 1: Write v5-github-integration.md

This doesn't exist yet. Write it.

**What to include:**
- GitHub Actions workflow (YAML) for each repo
- Webhook handler design (FastAPI endpoints)
- Issue-to-bounty flow
- PR-bounty linking strategy
- Label/sync flow
- Failure recovery design
- Notification templates (what the bot says on PRs/issues)

**Read these first:**
1. `/home/st9797/.openclaw/workspace/algo-bounty-design/v4-dashboard-api.md` — for API endpoints and notification design
2. `/home/st9797/.openclaw/workspace/algo-bounty-design/v6-hitm-design.md` — for HITM workflow
3. `/home/st9797/.openclaw/workspace/algo-bounty-design/escrow.algo` — for state machine
4. `/home/st9797/.openclaw/workspace/algo-bounty-design/v1-teal-escrow-contract.md` — for contract methods

### Priority 2: Expand escrow.algo

Add these methods from the v6 spec:
- `hitm_approve()` — creator approves work
- `hitm_reject()` — creator rejects work with reason
- `hitm_dispute()` — either party disputes
- `hitm_resolve_dispute()` — mediator resolves
- `hitm_auto_release()` — auto-release if review expires

### Priority 3: Build the Gateway (v4 spec)

The FastAPI gateway is the brain:
- All REST API endpoints from v4 spec
- GitHub webhook receiver
- Indexer poller (checks escrow state every 5 seconds)
- Telegram bot (for notifications)\n- SSE event stream (for real-time dashboard)
- Wallet signature auth

### Priority 4: Write Tests

Test plan from v1 spec + new tests for:
- HITM mode flows
- GitHub integration flows
- Karma system
- Edge cases (timeout, dispute, ghosting, etc.)

### Priority 5: Deploy

- GCP Cloud Run (see v4 architecture)
- Algorand sandbox node
- SQLite for MVP, Postgres at scale

---

## Key Technical Details

### Algorand Node Setup

```bash
# Local sandbox node
algod -d /tmp/algod
# Indexer
indexer -d /tmp/algod

# PyAlgoSDK
pip install algosdk pyteal puya

# Or use AlgoKit (recommended)
pip install algokit
```

### Puya/pyTEAL Notes

- Inner transactions for payouts
- Box storage for large data
- AppLocalStore for state
- Events/logs for off-chain processors
- RekeyTo protection for contracts

### Gateway Tech Stack

```
Python 3.12+
FastAPI + Uvicorn
PyAlgoSDK (Algorand interaction)
SQLAlchemy (database)
SQLite → PostgreSQL
Redis (caching, pub/sub)
aiohttp (webhooks)
python-telegram-bot (notifications)
Next.js (frontend)
```

---

## Environment

- **Server:** 10.0.0.67 (DGX Spark GB10)
- **User:** st9797
- **SSH:** SSH key at ~/.ssh/id_ed25519 (owner must provide)
- **Algorand:** Local sandbox node available
- **GitHub:** Owner must provide token for integration work
- **Workspace:** /home/st9797/.openclaw/workspace/

---

## Common Questions

**Q: Do I need to write the escrow contract from scratch?**
A: No. `escrow.algo` already exists (25KB). Add HITM methods and expand tests.

**Q: Is there a database already?**
A: No. Start with SQLite (per v4 spec), migrate to PostgreSQL at scale.

**Q: Can I use existing Algorand projects as references?**
A: Yes. AlgoKit is recommended. PyAlgoSDK is the standard library.

**Q: How do I test the escrow contract?**
A: Run `python tests/test_escrow_contract.py` — basic tests exist.

**Q: What's the file structure for new code?**
```
algo-gateway/        # FastAPI gateway
  api/               # REST endpoints
  hitm.py            # HITM service
  indexer.py         # Indexer poller
  telegram.py        # Bot integration
algo-bounty-design/  # Design docs (read these!)
algo-bounty-contract/  # Escrow contract (expand escrow.algo here)
algo-bounty-dashboard/  # Frontend (Next.js)
```

---

## What to Do Next

1. **Read v7-handover.md** — complete project overview
2. **Write v5-github-integration.md** — the missing design doc
3. **Expand escrow.algo** — add HITM methods
4. **Build the gateway** — FastAPI per v4 spec
5. **Write tests** — comprehensive test suite
6. **Deploy** — GCP Cloud Run per v4 architecture
7. **Alpha test** — with real AI agents

---

*This brief is a living document. Update it as you learn more.*
