# AlgoBounty v6: HITM (Human-in-the-Middle) Mode Design

**Status:** Complete
**Date:** 2026-06-30

---

## 1. Overview

HITM mode is an **optional validation layer** on top of the escrow contract. When enabled, it adds a human review period between work submission and escrow release, protecting both creators (from substandard work) and workers (from ghosting).

### Design Philosophy
- HITM is **opt-in per-bounty**, not mandatory
- Creator sets `is_hitm=1` at bounty creation time
- Auto-release as fallback when human review is delayed
- Dispute resolution for disagreements

---

## 2. Mode Selection Matrix

| Karma Score | HITM Required? | Default Mode | Notes |
|-------------|----------------|--------------|-------|
| 0–5 (Novice) | **Yes** (first 3 bounties only) | HITM | Protects creators from inexperienced workers |
| 6–15 (Emerging) | Optional | HITM | Can opt for trustless, but default is HITM |
| 16–50 (Established) | No | Trustless | Can choose either mode freely |
| 51+ (Trusted) | No | Trustless | No HITM needed; auto-release only |

### Novice Tier Mechanics
- New account starts with **Novice** status
- First 3 bounties they claim **must** use HITM mode (enforced by gateway)
- After 3 completed bounties with ≥ 75% positive outcomes → promoted to Emerging
- If a novice bounty is rejected 2+ times → demoted back to Novice (reset count)

---

## 3. HITM Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ HITM WORKFLOW (is_hitm=1)                                                │
│                                                                          │
│  [Creator]                                                              │
│    │                                                                    │
│    ├──► create_bounty(is_hitm=1, review_days=7) ──► ESCROW LOCKED       │
│    │                                      State: OPEN                  │
│    │                                                                    │
│  [Worker]                                                               │
│    │                                                                    │
│    ├──► claim_bounty() ──► State: CLAIMED                               │
│    │                                                                    │
│    ├──► submit_proof(pr_url, proof_data) ──► State: SUBMITTED           │
│    │                                      HITM review window: 7 days    │
│    │                                      Timer started ⏱               │
│    │                                                                    │
│    │    ┌─────────────────────────────────────────────┐                 │
│    │    │ REVIEW WINDOW (7 days)                       │                 │
│    │    │                                              │                 │
│    │    │  Creator options:                            │                 │
│    │    │    ├► approve_work() ──► State: CLOSED      │                 │
│    │    │    │                            payout=PAYOUT│                 │
│    │    │    │                            to=WORKER    │                 │
│    │    │    │                                          │                 │
│    │    │    ├► reject_work(reason) ──► State: REJECTED│                 │
│    │    │    │                            Worker must:  │                 │
│    │    │    │                            ├► revise    │                 │
│    │    │    │                            └► dispute   │                 │
│    │    │    │                                          │                 │
│    │    │    └► TIMEOUT (>7 days) ──► State: CLOSED   │                 │
│    │    │                                payout=PAYOUT│                 │
│    │    │                                to=WORKER    │                 │
│    │    │                                (auto-release)│                 │
│    │    └─────────────────────────────────────────────┘                 │
│    │                                                                    │
│  [Dispute Path]                                                         │
│    │                                                                    │
│    └──► dispute() ──► State: DISPUTED                                  │
│                         ├► creator_win  ──► payout=PAYOUT to=CREATOR   │
│                         ├► worker_win   ──► payout=PAYOUT to=WORKER   │
│                         └► split_50_50  ──► payout=SPLIT               │
│                                                                        │
│  [Timeout Fallback]                                                     │
│    └──► If dispute unresolved > 30 days ──► State: DISPUTED_TIMEOUT    │
│                                        └─► payout=SPLIT 50/50           │
│                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. State Machine Integration with escrow.algo

| escrow.algo State | HITM Interpretation |
|-------------------|---------------------|
| OPEN | Waiting for claim (HITM flag set at creation) |
| CLAIMED | Worker started work |
| SUBMITTED | Work submitted → HITM review window started |
| REJECTED | Creator rejected → worker can revise (up to 3x) or dispute |
| DISPUTED | Either party disputed → resolution needed |
| CLOSED | Completed (either via approve, auto-release, or dispute resolution) |
| DISPUTED_TIMEOUT | Dispute expired → 50/50 split |
| CLAIM_EXPIRED | Worker ghosted → reverts to OPEN |

### HITM-Specific Box Storage
```
_k_hitm_enabled      : uint64  — 1 if HITM mode active
_k_review_deadline   : uint64  — timestamp when review window ends
_k_rejection_count   : uint64  — number of rejections (max 3)
_k_dispute_reason    : bytes   — reason for dispute (max 256 chars)
_k_dispute_initiator : address — who initiated dispute
```

---

## 5. HITM Service Layer (Off-Chain)

### Architecture
```
┌────────────────────────────────────────────────────────────┐
│                     AlgoBounty HITM Service                 │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Indexer Poller   │  │  Notification     │               │
│  │  (5s interval)    │  │  Router           │               │
│  └────────┬─────────┘  └────────┬─────────┘               │
│           │                     │                           │
│  ┌────────▼─────────────────────▼─────────┐               │
│  │           HITM Orchestrator             │               │
│  │  ┌─────────────────────────────────┐   │               │
│  │  │ Review Timer Manager            │   │               │
│  │  │ - Tracks all active reviews     │   │               │
│  │  │ - Sends reminders at 75% mark   │   │               │
│  │  │ - Triggers auto-release at 100% │   │               │
│  │  └─────────────────────────────────┘   │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Telegram Bot     │  │  GitHub Comment   │               │
│  │  Integration      │  │  Integration      │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────────────────────────────────────────┘
```

### Service Components

**A. Indexer Poller**
- Polls Algorand indexer every 5 seconds
- Filters for app calls to escrow contract with HITM=1 and state=SUBMITTED
- When detected: creates review ticket, starts timer, notifies creator

**B. Review Timer Manager**
- In-memory timer with SQLite durability (checkpoint every 60s)
- Tracks: bounty_id, creator, review_deadline, notification_sent
- Actions:
  - At 75% of review window: sends reminder to creator
  - At 100%: triggers auto-release (worker protection)
  - On approve/reject: cancels timer

**C. Notification Router**
- Channels: Telegram (@each_user), GitHub comments, in-app notifications
- Templates:
  - `review_requested`: "New HITM review for bounty #123. Review period: 7 days."
  - `review_reminder`: "Bounty #123 review deadline in 2 days. Please review."
  - `review_expired`: "Bounty #123 auto-released to worker (review timeout)."
  - `changes_requested`: "Bounty #123: creator requested changes. Revise or dispute."

---

## 6. Dispute Resolution Flow

### Dispute Timeline
```
Day 0: Worker submits work (or creator rejects work)
Day 0: Either party calls dispute()
      ├► State: DISPUTED
      ├► Funds locked in dispute escrow
      └► Mediator notified (or community vote starts)

Day 0–30: Resolution window
      ├► Mediator review
      ├► Creator_win → payout to creator
      ├► Worker_win → payout to worker
      └► split_50_50 → 50% each

Day 30: TIMEOUT
      └► payout=SPLIT 50/50 (automatic)
      └► Both parties lose 1 karma point
```

### Dispute Resolution Options
1. **Creator wins** — Work doesn't meet requirements → full refund
2. **Worker wins** — Creator's rejection was invalid → worker gets paid
3. **Split 50/50** — Compromise or timeout → both parties share

### Mediator Selection
- Creator specifies mediator at bounty creation (optional)
- If no mediator: platform-verified mediators can claim the dispute
- Mediators earn platform fee (0.5% of escrow) as incentive
- Unverified mediators can participate but earn no fee

---

## 7. Failure Cases & Mitigations

| Failure Case | Mitigation |
|--------------|------------|
| Creator ghosts after submission | Auto-release after review window (7 days default) |
| Worker ghosts after claim | Bounty reverts to OPEN after claim timeout (48h) |
| Creator rejects valid work | Worker can dispute → 50/50 or full payout |
| Creator accepts poor work | Harder to prevent; mitigated by karma (bad payouts hurt creator's karma if reported) |
| Dispute mediator goes offline | 30-day timeout → 50/50 split |
| HITM service goes down | Indexer polling detects state changes independently; auto-release still works |
| Creator disputes everything | Dispute timeout at 30 days → 50/50 split, both lose karma |
| Worker submits garbage repeatedly | Karma penalties (-3 for fake/broken work) |

---

## 8. Contract Method Signatures (Puya/pyTEAL)

```python
@Methods.external()
def hitm_approve(self, bounty_id: Bytes) -> UInt64:
    """Creator approves submitted work."""
    # Requires: state==SUBMITTED, is_hitm==1, sender==creator
    # Effects: state=CLOSED, payout_type=PAYOUT, payout to worker

@Methods.external()
def hitm_reject(self, bounty_id: Bytes, reason: Bytes) -> UInt64:
    """Creator rejects work, requests changes."""
    # Requires: state==SUBMITTED, is_hitm==1, sender==creator
    # Effects: state=REJECTED, store reason, max 3 rejections allowed

@Methods.external()
def hitm_dispute(self, bounty_id: Bytes, reason: Bytes) -> UInt64:
    """Either party initiates dispute."""
    # Requires: state in (SUBMITTED, REJECTED), sender == creator or worker
    # Effects: state=DISPUTED, start 30-day timer

@Methods.external()
def hitm_resolve_dispute(self, bounty_id: Bytes, resolution: UInt64) -> UInt64:
    """Mediator resolves dispute: 0=creator_win, 1=worker_win, 2=split."""
    # Requires: state==DISPUTED, sender==verified_mediator
    # Effects: state=CLOSED, execute payout per resolution

@Methods.external()
def hitm_auto_release(self, bounty_id: Bytes) -> UInt64:
    """Any participant if review window expired."""
    # Requires: state==SUBMITTED, is_hitm==1, current_time > review_deadline
    # Effects: state=CLOSED, payout=PAYOUT to worker
```

---

## 9. Integration with v5 (Notification System)

### Event → Notification Mapping
| Event | Creator | Worker |
|-------|---------|--------|
| HITM review started | — | ✅ "Your submission is under review" |
| Creator approves | ✅ "Payment released!" | ✅ "You've been paid!" |
| Creator rejects | ✅ "Changes requested: {reason}" | ✅ "Creator requested changes" |
| Worker revises | ✅ "Worker submitted revised work" | — |
| Dispute opened | ✅ "Dispute opened" | ✅ "Dispute opened" |
| Dispute resolved | ✅ "Dispute resolved: {outcome}" | ✅ "Dispute resolved: {outcome}" |
| Auto-release triggered | ✅ "Bounty auto-released (timeout)" | ✅ "Bounty auto-released to you!" |
| Review reminder (75%) | ✅ "Review deadline approaching" | — |

### GitHub Integration
- If bounty linked to GitHub repo: bot comments on relevant PR/issue
- Status check: `algobounty/hitm-review` — pending/approved/rejected
- Label sync: `bounty:reviewing` → `bounty:approved` or `bounty:disputed`

### Telegram Integration
- Direct messages to creator/worker via their Telegram chat_id
- Inline buttons: `✅ Approve` | `❌ Reject` | `⚠️ Dispute`
- Auto-timeout if no response within review window

---

## 10. Implementation Priority

### Phase 1: Core HITM
- [ ] hitm_approve(), hitm_reject(), hitm_auto_release() in escrow.algo
- [ ] HITM service indexer poller
- [ ] Telegram notification integration

### Phase 2: Dispute Resolution
- [ ] hitm_dispute(), hitm_resolve_dispute()
- [ ] Mediator registry
- [ ] 30-day timeout with 50/50 split

### Phase 3: Enhanced Features
- [ ] Community voting for disputes (>1000 meditations?)
- [ ] GitHub status check integration
- [ ] Karma scoring for HITM outcomes (creator fairness, worker responsiveness)

---

## Appendix: Auto-Release Protection

### Why Auto-Release is Critical
Without auto-release, a creator can:
1. Wait for worker to submit work
2. Never call approve_work() or reject_work()
3. Worker gets nothing, creator gets nothing (funds permanently locked)

**Auto-release solves this**: if the review window expires without action, funds automatically go to the worker. This is the worker's protection against ghosting.

### Review Window Configuration
| Setting | Default | Min | Max |
|---------|---------|-----|-----|
| review_days | 7 | 1 | 30 |
| reminder_threshold | 75% | 50% | 90% |
| dispute_timeout_days | 30 | 7 | 60 |

---

*Design complete. Ready for implementation as Phase 3 after v1-v2 core contracts.*
