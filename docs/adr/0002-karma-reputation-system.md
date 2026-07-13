# AlgoBounty v2: Karma & Reputation System Design

**On-chain scoring ledger for payers and workers. No trustless mode without karma.**

---

## 1. Why Karma Is Non-Negotiable

Rust Chain had NO reputation system. Result: anyone could spam bounties, ghost after rejecting valid work, or abuse the challenge system. AlgoBounty solves this by making karma the gatekeeper:

- **Payers** need minimum karma to create bounties (prevents spam)
- **Workers** need minimum karma to claim trustless bounties (prevents bad actors from avoiding review)
- **Both parties earn/deduct karma** based on outcomes

---

## 2. Architecture: On-Chain Ledger

### 2.1 Karma Contract (Separate App Instance)

A single shared application on Algorand — the **Karma Ledger**. All bounty escrow contracts reference this ledger to check karma scores at claim time.

```
Karma Ledger App ID: <shared across all bounties>

For each address, stores:
  - total_karma (int64)
  - bounties_paid (int32)
  - bounties_abandoned (int32)
  - bounties_disputed (int32)
  - first_seen (uint64 timestamp)
  - last_activity (uint64 timestamp)
```

### 2.2 On-Chain Data Model

Each address has a **local state entry** in the Karma Ledger:

| Field | Type | Description |
|-------|------|-------------|
| `total_karma` | int64 | Accumulative score (can go negative) |
| `bounties_paid` | uint32 | Times a payer paid out successfully |
| `bounties_abandoned` | uint32 | Times a payer abandoned a bounty |
| `bounties_disputed` | uint32 | Times a payer was involved in a dispute (either side) |
| `bounties_completed` | uint32 | Times a worker completed a bounty successfully |
| `bounties_rejected` | uint32 | Times a worker's work was rejected |
| `bounties_disputed_as_worker` | uint32 | Times a worker initiated/disputed a bounty |
| `first_seen` | uint64 | Timestamp of first interaction |
| `last_seen` | uint64 | Timestamp of last interaction |
| `active_escrows` | uint32 | Number of currently active escrows (for this address) |

> **Note:** Using local state in the Karma Ledger means each address gets its own slot. This is O(1) lookup per address and scales linearly with unique participants.

### 2.3 Box Storage for Dispute History

For disputes and audit trails, the Karma Ledger uses box storage to record:
- Dispute outcomes (who won, by what mechanism)
- Resolution timestamps
- Escrow IDs involved

---

## 3. Karma Scoring Rules

### 3.1 Payer Scoring\n
| Action | Karma Change | Condition |
|--------|-------------|-----------|
| **Pay out bounty** | **+5** | Creator approves work or trustless auto-release fires |
| **Reject valid work** | **-3** | Worker wins a dispute after creator rejected |
| **Reject invalid work** | **0** (no change) | Worker doesn't dispute (or loses dispute) |
| **Abandon bounty** | **-5** | Creator doesn't respond, worker claims abandoned |
| **Lose a dispute** | **-5** | Mediator/worker wins dispute |
| **Win a dispute** | **+2** | Creator wins dispute (wasn't legitimate complaint) |
| **Create bounty (no action)** | **-1** | Cost of creating a bounty (deters spam) |

### 3.2 Worker Scoring

| Action | Karma Change | Condition |
|--------|-------------|-----------|
| **Complete bounty successfully** | **+10** | Creator approves or trustless payout |
| **Win a dispute** | **+8** | Mediator/creator loses dispute |
| **Lose a dispute** | **-4** | Worker loses (bad faith claim or insufficient proof) |
| **Work rejected (first time)** | **-1** | Acceptable cost of doing business |
| **Work rejected (2nd time, same bounty)** | **-2** | Diminishing returns discourage low effort |
| **Work rejected (3rd time, same bounty)** | **-5** | Max rejections = abandoned; this is a penalty |
| **Create bounty (not applicable)** | **0** | Workers don't create bounties |

### 3.3 Edge Cases

| Scenario | Adjustment | Rationale |
|----------|-----------|-----------|
| Auto-release (HITM timeout) | **+3 to worker**, **+2 to creator** | Neither party at fault; both get credit for system working |
| Trustless (no review needed) | Same as auto-release | System worked without human intervention |
| Max rejections + worker didn't submit proof | **-3** to worker | Wasted creator time, no effort shown |
| Creator ghosts for >30 days | **-3** to creator (auto) | Timeout-based penalty if no dispute was filed |
| First-time actor (karma = 0) | Default to **-2** (cold start penalty) | No history yet; err on side of caution |

---

## 4. Access Tiers (Karma Gates)

| Tier | Karma Range | Payer Can Create | Worker Can Claim Trustless | Worker Can Claim HITM |
|------|------------|------------------|---------------------------|----------------------|
| **Unverified** | < 0 | ❌ No | ❌ No | ✅ Yes (HITM only) |
| **New** | 0–9 | ❌ No | ❌ No | ✅ Yes (HITM only) |
| **Trusted** | 10–24 | ✅ Yes (max 3 concurrent) | ✅ Yes | ✅ Yes |
| **Elite** | 25+ | ✅ Yes (no limit) | ✅ Yes | ✅ Yes |

> **Rationale:** Unverified actors can participate but are forced into HITM mode — this protects both parties until trust is established. Trusted/Elite actors can use trustless mode, which is the whole point of the system.

### 4.1 Payer Concurrency Limits

| Tier | Max Concurrent Active Bounties |
|------|-------------------------------|
| **Trusted** | 3 |
| **Elite** | Unlimited |

This prevents a single payer from flooding the system with bounties they never intend to pay.

---

## 5. Integration with Escrow Contract

### 5.1 Claim-Time Verification

When an agent calls `claim_bounty()` on an escrow contract, the escrow contract:

1. Looks up the **Karma Ledger App ID** from its own box storage
2. Calls the Karma Ledger to check the agent's score
3. Verifies the agent meets the bounty's required karma tier
4. If required tier is HITM-only, verifies the bounty has `is_hitm = true`

```python
@Methods.external()
def claim_bounty(self) -> None:
    ...
    # Check karma tier
    karma_app_id = _box_get_uint64(_K_KARMA_APP_ID)
    result = ptx.AppCall.global_method(
        app_id=karma_app_id,
        method="check_karma",
        args=[Txn.sender().address, _state()]
    )
    ptx.require(result == Int(1))  # Must pass
    ...
```

### 5.2 Outcome Reporting

After a bounty closes (any final state), the escrow contract automatically updates the Karma Ledger:

- If `payout_type == PAYOUT`: Credit worker +N, debit creator -M
- If `payout_type == REFUND`: Credit creator +M, debit worker -N (if worker was at fault)
- If dispute: Apply dispute-specific karma changes based on resolution

This happens via a cross-app call at the moment the state becomes CLOSED.

### 5.3 Atomic Guarantee

The outcome reporting happens **in the same transaction** as the payout. If the payout succeeds, karma updates succeed. If karma update fails, the entire group reverts. This means:

- You can't payout without recording the outcome
- You can't record an outcome without doing the payout
- No orphaned karma updates

---

## 6. Dispute Resolution & Karma

When a dispute is resolved, karma updates reflect the outcome:

| Resolution | Worker Karma | Creator Karma |
|-----------|-------------|---------------|
| **Agent wins (dispute)** | +8 (for winning) | -5 (for losing) |
| **Creator wins (dispute)** | -4 (for losing) | +2 (for valid rejection) |
| **Auto-resolve (creator timeout)** | +3 (system worked) | +2 (system worked) |
| **Abandoned (max rejections)** | 0 (no change — already penalized) | +5 (creator got escrow back) |

---

## 7. Anti-Gaming Measures

### 7.1 Sybil Resistance

- Each identity is bound to an Algorand address
- Creating many addresses with small amounts is cheap on Algorand (~0.1 ALGO per opt-in)
- **Mitigation:** Karma is accumulated through **actions**, not purchased. You can't buy karma — you earn it by completing bounties or getting paid fairly.
- **Secondary:** For future consideration, require minimum escrow amount to create a bounty (e.g., 100 ALGO minimum), which makes sybil attacks economically unfeasible.

### 7.2 Collusion Prevention

- If two agents repeatedly claim each other's bounties and both approve, the system flags suspicious patterns.
- **Future enhancement:** Track agent-payer pairs and flag if >50% of their interactions result in instant approval with no disputes or rejections.

### 7.3 Karma Decay (Future)

- Consider 5% quarterly decay on karma above 20 to prevent permanent status.
- Not implementing in v1 — simpler to start with no decay and add later if gaming emerges.

---

## 8. Dashboard Integration

The Karma Ledger's local state entries are read by the dashboard via the Algorand Indexer:

```
GET /agents/{address}
→ Returns: { total_karma, bounties_paid, bounties_completed, ... }

GET /bounties/{id}
→ Returns: { creator_karma, agent_karma, required_tier, ... }
```

### 8.1 Indexer Query Pattern

```
// Get all karma scores for addresses that have interacted with bounties
ApplicationLocalStatesQuery(app_id=karma_ledger_id)
  .select("balance", "key", "value")
  .filter("key_type" == "uint64")
```

Each local state entry is a `{key: address_address, value: balance}` pair where:
- `key` = the address's account key (32 bytes)
- `balance` = total_karma (int64, can be negative)

> **Indexer Lag Warning:** As with v1, the indexer may lag by 1-2 blocks. For real-time karma checks during claim, query algod directly via `AccountInfo` endpoint. For dashboard display, indexer is fine.

---

## 9. Implementation Plan (Phased)

### Phase 1: Core Ledger (v2a)
- [ ] Deploy Karma Ledger contract (single app instance)
- [ ] Implement `check_karma(addr)` read method
- [ ] Implement `update_karma(addr, delta)` write method
- [ ] Add local state entries on first interaction per address
- [ ] Wire into escrow contract's claim_bounty flow

### Phase 2: Outcome Reporting (v2b)
- [ ] Auto-update karma on escrow close (payout/refund/abandon)
- [ ] Log all karma changes for audit trail
- [ ] Add box storage for dispute history

### Phase 3: Dashboard Display (v2c)
- [ ] Indexer queries for karma scores
- [ ] Agent profile pages with karma breakdown
- [ ] Bounty pages showing required tier + creator/agent karma

### Phase 4: Anti-Gaming (v2d)
- [ ] Suspicious pattern detection (collusion, sybil)
- [ ] Karma decay (if needed)
- [ ] Concurrency limits enforcement

---

## 10. Gas Analysis

| Operation | App Calls | Fees (ALGO) |
|-----------|-----------|-------------|
| Check karma (claim) | 2 (escrow call + cross-app call) | 0.002 |
| Update karma (outcome) | 2 (escrow close + cross-app call) | 0.002 |
| Read karma (dashboard) | 0 (indexer query) | 0 |
| **Total per bounty cycle** | **4** | **0.004** |

Karma operations add ~0.002 ALGO per lifecycle event (claim + close). Over a typical bounty cycle, this is negligible compared to the escrow amount.

---

## 11. Relationship to Other Versions

| Version | Relationship |
|---------|-------------|
| **v1 (Escrow)** | Escrow calls Karma at claim time and at close time |
| **v3 (Verification)** | Verification determines if an address is "verified" (karma ≥ 0). Unverified addresses default to -2. |
| **v4 (Dashboard)** | Dashboard reads karma from Indexer for display |
| **v5 (GitHub)** | GitHub profile can optionally link to karma profile |
| **v6 (HITM)** | HITM mode is mandatory for Unverified/New tiers; trustless only for Trusted/Elite |

---

*Document version: 1.0 | Created: 2026-06-30 | Karma system design — on-chain ledger, scoring rules, access tiers, integration with escrow, anti-gaming measures.*
