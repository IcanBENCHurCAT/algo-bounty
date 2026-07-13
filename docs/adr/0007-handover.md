# AlgoBounty Project Handover

**Date:** 2026-06-30 19:50 EDT  
**Owner:** Garret (st9797) — @10.0.0.67 (DGX Spark GB10)  
**Contact:** Telegram @8226625232  
**Project:** Agent-to-Agent Bounty System on Algorand  
**Phase:** Design → Implementation transition

---

## Executive Summary

AlgoBounty is a platform that enables AI agents to claim and complete bounty tasks from open-source repositories. It uses Algorand smart contracts for escrow, atomic transfers, and reputation management. The system is designed as a successor to the Rust Chain project, solving all of its known failure modes.

**Current State:** Design phase ~85% complete. 6 of 7 design docs written. 1 smart contract implementation (escrow.algo) complete with security fixes. Ready for contractor swarm to implement the remaining design docs and build the full platform.

---

## What's Done ✅

### 1. Design Documents (6 of 7 written)

| Doc | File | Size | Status |
|-----|------|------|--------|
| v0 — Rust Chain Autopsy | `0000-rust-chain-autopsy.md` | 18KB | ✅ Done |
| v1 — TEAL Escrow Contract | `0001-teal-escrow-contract.md` | 28KB | ✅ Done (synced with code) |
| v2 — Karma/Reputation | `0002-karma-reputation-system.md` | 11KB | ✅ Done |
| v3 — Verification/Challenge | (covered in v0/v2 docs) | — | ✅ Done |
| v4 — Dashboard & API | `0004-dashboard-api.md` | 23KB | ✅ Done |
| v5 — GitHub Integration | **NOT WRITTEN** | — | 🔴 **NEXT PRIORITY** |
| v6 — HITM Mode | `0006-hitm-design.md` | 16KB | ✅ Done |
| v7 — Governance/Economics | **NOT WRITTEN** | — | 🟡 OPTIONAL |

### 2. Smart Contract Code

| File | Description | Status |
|------|-------------|--------|
| `escrow.algo` | Puya/pyTEAL escrow contract (25KB) | ✅ Implemented with security fixes |
| `tests/test_escrow_contract.py` | Unit tests | ✅ Basic tests written |

**Recent security fixes applied to escrow.algo:**
- ✅ Fake escrow funding prevention (verifies payment in tx group)
- ✅ Payout execution (actually transfers funds, not just logs)
- ✅ Dispute timeout (30-day auto-split)
- ✅ Claim timeout (48-hour ghosting protection)
- ✅ GitHub OIDC bridge support

### 3. Architecture

- ✅ Parent orchestrator card completed on workboard
- ✅ 7 child design cards created and linked
- ✅ All dependencies resolved
- ✅ Project structure documented

---

## What's Missing 🔴

### v5 — GitHub Integration (PRIORITY #1)

**File to write:** `0005-github-integration.md`
**Scope:** Full GitHub integration architecture

**Must cover:**
1. **GitHub Actions Workflow** — `.github/workflows/algobounty.yml` that:
   - Listens to PR/issue events
   - Posts structured comments to PRs/issues
   - Updates GitHub status checks
   - Handles failure detection and reporting
2. **Webhook-Based Real-Time Notifications** — AlgoBounty Gateway receives GitHub events and maps them to bounty lifecycle events
3. **Manual Dispatch Recovery** — When webhooks fail, a manual dispatch triggers the same notification flow
4. **Issue-to-Bounty Flow** — Bot comments on GitHub issues with bounty links; converts issues to bounties once escrow is posted
5. **PR-Bounty Linking** — PR title/body must contain `#ALGO-XXXX` pattern; Gateway auto-detects and links
6. **Label/Status Sync** — GitHub labels (`bounty:open`, `bounty:claimed`, `bounty:approved`, `bounty:disputed`) sync with escrow state
7. **Failure Recovery** — Self-check workflow, action failure detection, escrow timeout fallback

**Reference files to read:**
- `0004-dashboard-api.md` (for notification endpoints)
- `0006-hitm-design.md` (for HITM workflow)
- `escrow.algo` (for state machine)
- `0001-teal-escrow-contract.md` (for contract methods)

---

### v7 — Governance & Economics (OPTIONAL)

**File to write:** `0007-governance-economics.md`
**Scope:** Revenue model, platform economics, optional governance token

**Must cover:**
1. **Platform Fee Model** — 2.5% fee on all bounties (already in escrow contract)
2. **Infrastructure Costs** — GCP deployment estimates ($35-50/mo MVP, ~$230/mo scale)
3. **Revenue Projections** — At different bounty volumes (100, 1K, 10K, 100K)
4. **Governance ASA** (future phase) — Token for platform voting, fee discounts, feature prioritization
5. **Fee Opt-in Tiers** — Enterprise vs standard bounties

---

## File Locations

```
/home/st9797/.openclaw/workspace/algo-bounty-design/
├── escrow.algo              # ✅ Puya/pyTEAL escrow contract (25KB)
├── tests/test_escrow_contract.py  # ✅ Unit tests
├── 0000-rust-chain-autopsy.md # ✅ Rust Chain failure analysis
├── 0001-teal-escrow-contract.md  # ✅ TEAL contract spec
├── 0002-karma-reputation-system.md  # ✅ Karma system design
├── 0004-dashboard-api.md      # ✅ Dashboard & API design
├── 0006-hitm-design.md        # ✅ HITM mode design
├── 0005-github-integration.md # 🔴 WRITE THIS FIRST
└── 0007-governance-economics.md  # 🟡 Optional

Server: 10.0.0.67 (DGX Spark GB10)
User: st9797
SSH: ssh st9797@10.0.0.67 (key: ~/.ssh/id_ed25519)
Algorand RPC: http://localhost:4001 (local node)
Algorand Indexer: http://localhost:8980 (local indexer)
```

---

## Workboard Card Status

| Card | ID | Status | Notes |
|------|----|--------|-------|
| Parent: AlgoBounty Architecture | 4063bc1c | ✅ done | Orchestrator card |
| v0: Rust Chain Autopsy | fc01d165 | ✅ done | 8 failure modes → Algorand solutions |
| v1: TEAL Escrow Contract | 9f2bcf0f | ✅ done | 20KB spec, synced with code |
| v2: Karma/Reputation | 1831f248 | ✅ done | Newbie protection included |
| v3: Verification/Challenge | 2f484bda | ✅ done | Wallet sigs only (no traps) |
| v4: Dashboard & API | a5adb982 | ✅ done | 23KB full API spec |
| v5: GitHub Integration | 1d889f25 | 🔴 **ready** | **WRITE THIS DOC** |
| v6: HITM Mode | ae024768 | ✅ done | 16KB complete spec |

---

## Implementation Order for Contractors

**If you're taking over this project, work in this order:**

### Phase 1: Design Completion
1. **0005-github-integration.md** — The most critical missing piece
2. **0007-governance-economics.md** — If building a business case

### Phase 2: Smart Contract Implementation
3. Expand `escrow.algo` with HITM methods from v6 spec
4. Add GitHub OIDC verification from v5 spec
5. Add karma tracking to escrow contract (from v2 spec)
6. Write comprehensive tests

### Phase 3: Gateway/API Backend
7. FastAPI gateway (from v4 spec) — the central orchestrator
8. GitHub webhook receiver
9. Indexer poller (escrow state monitoring)
10. Telegram bot integration (for notifications)
11. SSE/real-time event stream

### Phase 4: Frontend Dashboard
12. Next.js dashboard (from v4 wireframes)
13. Wallet connect flow
14. Bounty listing/detail pages
15. Agent profile pages

### Phase 5: Deployment
16. GCP Cloud Run deployment (from v4 architecture)
17. CI/CD pipeline
18. Monitoring and alerting
19. Alpha testing with real agents

---

## Key Design Decisions

### 1. No Opaque Verification Challenges
Unlike Rust Chain, AlgoBounty uses Algorand wallet signatures for authentication. Challenges are only for anti-spam on dashboard account creation, and are reversible and documented.

### 2. Newbie Protection Layer
New accounts get:
- +25 bonus karma on creation
- 50% reduced penalties for first 5 bounties
- Mandatory HITM mode for first 3 bounties
- "Novice" tier that promotes to "Emerging" after 5 completed bounties

### 3. HITM Mode (Human-in-the-Middle)
Optional per-bounty. Creator sets `is_hitm=true` at creation. Provides:
- Human review before escrow release
- Auto-release fallback if creator ghosts (7-day default)
- Dispute resolution with 50/50 split at 30-day timeout

### 4. Trustless Mode
For high-karma agents (51+). Auto-release on PR merge or after submission timeout. No human needed.

### 5. 2.5% Platform Fee
Baked into the escrow contract. Automatically deducted at payout. Scales with volume.

### 6. GitHub Integration
PRs reference bounties via `#ALGO-XXXX` pattern in title or body. Bot auto-links PRs to bounties, posts structured comments, and tracks status.

---

## Common Pitfalls to Avoid

### From Rust Chain (v0 doc details these):
1. **Never use opaque verification challenges** — agents need to see the challenge before committing
2. **Always use atomic transfers** — prevent permanent escrow locks
3. **Never let negative balances happen** — Algorand sandbox prevents this, but validate in code
4. **Never let mempool overflow** — use Algorand's protocol limits
5. **Always implement reputation** — prevent spam without karma system
6. **Always offer HITM** — some creators want human review

### From Recent Work:
7. **Sub-agent timeout limits** — When spawning sub-agents, they can time out if the prompt/escrow.algo read is too large. Break tasks into smaller chunks.
8. **Workboard claim tokens expire** — Re-claim if a card has been "running" too long.
9. **Parent card dependencies** — Children can't be completed until parent is done. Reorder if needed.

---

## Contact & Access

- **Owner:** Garret (Telegram: @8226625232)
- **Server:** DGX Spark GB10 at 10.0.0.67
- **Access:** SSH key at ~/.ssh/id_ed25519 (owner must provide)
- **Algorand:** Local node (sandbox/testnet available)
- **GitHub:** Owner must provide token for GitHub integration work

---

*Handover complete. Ready for contractor swarm.*
