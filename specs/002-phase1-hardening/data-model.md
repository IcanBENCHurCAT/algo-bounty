# Data Model: Phase 1 Pre-Mainnet Hardening

**Date**: 2026-07-25
**Feature**: [spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/002-phase1-hardening/spec.md)

## Entity Changes

### 1. Escrow State Machine (On-Chain — `escrow.py`)

#### State Constants (unchanged)
| State | Value | Description |
|-------|-------|-------------|
| OPEN | 0 | Bounty created, awaiting worker claim |
| CLAIMED | 1 | Worker has claimed, awaiting work submission |
| SUBMITTED | 2 | Work submitted, awaiting creator review |
| REJECTED | 3 | Work rejected by creator, worker can revise or escalate |
| DISPUTED | 4 | Under dispute resolution |
| CLOSED | 5 | Resolved (payout, refund, or split complete) |
| DISPUTED_TIMEOUT | 6 | Dispute timed out |
| CLAIM_EXPIRED | 7 | Worker's claim deadline passed |

#### State Transition Changes

**Modified: `claim_abandoned()` → time-gated only**
- Current precondition: `state == REJECTED AND rejection_count >= MAX_REJECTIONS AND sender == creator`
- New precondition: `state == REJECTED AND rejection_count >= MAX_REJECTIONS AND sender == creator AND latest_timestamp > last_rejection_timestamp + ABANDONMENT_TIMEOUT`
- New field: `last_rejection_timestamp` (BoxRef, UInt64) — set in `reject_work()` to `Global.latest_timestamp`
- New template var: `ABANDONMENT_TIMEOUT` — default 7 days (604800 seconds)
- Rationale: Creator can only reclaim funds after the worker has had 7 days to escalate

**New: `escalate_to_dispute()` — worker escalation after max rejections**
- Precondition: `state == REJECTED AND rejection_count >= MAX_REJECTIONS AND sender == agent_address`
- Effect: Sets `state = DISPUTED`, records `dispute_timestamp`, selects evaluators (same logic as `submit_dispute()`)
- Rationale: Gives the worker an explicit path to challenge final rejection

#### Rename: `arbitrator` → `evaluator`

| Old Name | New Name |
|----------|----------|
| `arbitrator_1` (BoxRef) | `evaluator_1` |
| `arbitrator_2` (BoxRef) | `evaluator_2` |
| `arbitrator_3` (BoxRef) | `evaluator_3` |
| `arbitrator_1_vote` (BoxRef) | `evaluator_1_vote` |
| `arbitrator_2_vote` (BoxRef) | `evaluator_2_vote` |
| `arbitrator_3_vote` (BoxRef) | `evaluator_3_vote` |
| `candidate_count` (BoxRef) | `candidate_count` (unchanged — generic) |
| `cand_addr_{idx}` (Box key) | `cand_addr_{idx}` (unchanged — generic) |
| `cand_idx_{addr}` (Box key) | `cand_idx_{addr}` (unchanged — generic) |
| `register_arbitrator()` (ABI) | `register_evaluator()` |
| `deregister_arbitrator()` (ABI) | `deregister_evaluator()` |
| `vote_dispute()` (ABI) | `vote_dispute()` (unchanged — generic) |
| Log: `arbitrator_registered` | Log: `evaluator_registered` |
| Log: `arbitrator_deregistered` | Log: `evaluator_deregistered` |
| Log: `arbitrator_voted` | Log: `evaluator_voted` |

---

### 2. AccountQuarantine (Off-Chain — New DB Table)

**Table name**: `account_quarantines`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, autoincrement | Record ID |
| `address` | String | NOT NULL, indexed | Quarantined wallet address |
| `reason` | String | NOT NULL | Reason for quarantine (e.g., "post_refund_merge") |
| `details` | Text | nullable | Additional context (bounty ID, PR URL, etc.) |
| `quarantined_at` | DateTime | NOT NULL, default=utcnow | When quarantine started |
| `expires_at` | DateTime | NOT NULL | When quarantine auto-expires (quarantined_at + 72 hours) |
| `status` | String | NOT NULL, default="active" | Enum: "active", "cleared", "penalized" |
| `resolved_by` | String | nullable | Admin address who resolved |
| `resolved_at` | DateTime | nullable | When admin resolved |
| `resolution_note` | Text | nullable | Admin's reason for clearing/penalizing |

**Validation rules**:
- `expires_at` MUST be `quarantined_at + 72 hours`
- Only one `active` quarantine per address at a time
- `resolved_by` MUST be a known admin address

---

### 3. Evaluator (Renamed from Arbitrator — DB Table)

**Table name**: `evaluators` (renamed from `arbitrators`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `address` | String | PK, indexed | Wallet address |
| `status` | String | NOT NULL, default="active" | Enum: "active", "inactive" |
| `registered_at` | DateTime | NOT NULL, default=utcnow | Registration timestamp |

**Table name**: `dispute_evaluators` (renamed from `dispute_arbitrators`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, autoincrement | Record ID |
| `bounty_id` | String | FK → bounties.bounty_id, NOT NULL | Related bounty |
| `evaluator_address` | String | FK → evaluators.address, NOT NULL | Assigned evaluator (renamed from `arbitrator_address`) |
| `vote` | String | nullable | Vote value: "worker", "payer", "split", "abstained" |
| `voted_at` | DateTime | nullable | When vote was cast |

---

### 4. SyncRecord (Off-Chain — New DB Table)

**Table name**: `sync_records`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, autoincrement | Record ID |
| `bounty_id` | String | FK → bounties.bounty_id, NOT NULL | Bounty being synced |
| `triggered_by` | String | NOT NULL | Address of user who triggered sync |
| `triggered_at` | DateTime | NOT NULL, default=utcnow | Sync timestamp |
| `github_state` | String | NOT NULL | Observed GitHub state (e.g., "merged", "closed", "open") |
| `action_taken` | String | NOT NULL | What the sync did (e.g., "status_updated", "no_change", "payout_ready") |
| `idempotency_key` | String | UNIQUE, NOT NULL | `{bounty_id}:{github_commit_sha}` or `{bounty_id}:{issue_close_event_id}` |

**Validation rules**:
- `idempotency_key` uniqueness prevents duplicate processing
- Rate limit: max 10 sync attempts per bounty per hour

---

### 5. Bounty (Existing — Modified Fields)

**Added field to existing `bounties` table**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `payout_ready` | Boolean | default=False | Set to True when manual sync confirms PR merge and worker can claim |
| `payout_ready_at` | DateTime | nullable | When payout became ready |

