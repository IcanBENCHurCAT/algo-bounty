# API Contract: Payout Fee Split

**Feature**: 006-fee-split-payouts

## ARC4 Contract Interface — Modified Methods

### `approve_work()`

**Action**: Payout the agent after creator approval

**Transaction Group Requirements** (single app call producing inner transactions):

| Index | Type | Key Fields |
|-------|------|-----------|
| 0 | AppCall | `approve_work()` |
| 1 | Inner: Payment/AssetTransfer | Recipient: creator, Amount: `escrow_amount * 2 // 200`, Fee: 0 |
| 2 | Inner: Payment/AssetTransfer | Recipient: treasury, Amount: `escrow_amount * 2 // 200`, Fee: 0 |
| 3 | Inner: Payment/AssetTransfer | Recipient: mediator, Amount: `escrow_amount * 25 // 10000`, Fee: 0 |
| 4 | Inner: Payment/AssetTransfer | Recipient: agent, Amount: `escrow_amount - (2% + 0.25%)`, Fee: 0 |

**Amount Computation**:
```
fee_total = escrow_amount * 2 // 100
royalty = fee_total // 2        # 1% (rounded down)
treasury = fee_total - royalty   # remainder of 2%
mediator = escrow_amount * 25 // 10000  # 0.25%
agent = escrow_amount - fee_total - mediator
```

**Asserts**:
- `Txn.rekey_to == Account(0)`
- `state == SUBMITTED`
- `Txn.sender == creator_address`
- Contract holds ≥ `escrow_amount` in specified asset

---

### `resolve_dispute(resolution, mediator_signature)`

**Action**: Resolve a dispute via mediator signature

**If resolution == "agent_win"** (PAYOUT):

| Index | Type | Key Fields |
|-------|------|-----------|
| 0 | AppCall | `resolve_dispute()` |
| 1 | Inner: Payment/AssetTransfer | Recipient: creator, Amount: `fee_total // 2`, Fee: 0 |
| 2 | Inner: Payment/AssetTransfer | Recipient: treasury, Amount: `fee_total - royalty`, Fee: 0 |
| 3 | Inner: Payment/AssetTransfer | Recipient: mediator, Amount: `0.25%`, Fee: 0 |
| 4 | Inner: Payment/AssetTransfer | Recipient: agent, Amount: `remainder`, Fee: 0 |

**If resolution == "creator_win"** (REFUND):

| Index | Type | Key Fields |
|-------|------|-----------|
| 0 | AppCall | `resolve_dispute()` |
| 1 | Inner: Payment/AssetTransfer | Recipient: treasury, Amount: `fee_total - royalty`, Fee: 0 |
| 2 | Inner: Payment/AssetTransfer | Recipient: mediator, Amount: `0.25%`, Fee: 0 |
| 3 | Inner: Payment/AssetTransfer | Recipient: creator, Amount: `remainder`, Fee: 0 |

**Note**: Index 1 (royalty payment to creator) is omitted because `creator_address == creator_recipient` — deduplication applies.

---

### `auto_release()`

**Action**: Auto-release HITM bounty after review deadline

**Transaction Group**: Same as `approve_work()` — 4 inner payments (royalty, treasury, mediator, agent).

---

### `_execute_arbitration_payout(consensus_option)`

**If consensus == 1** (agent_win, PAYOUT):

Same as `approve_work()` — 4 inner payments including royalty to creator.

**If consensus == 2** (creator_win, REFUND):

Same as `resolve_dispute(creator_win)` — royalty omitted (dedup), 3 inner payments.

**If consensus == 3** (split, SPLIT):

| Index | Type | Key Fields |
|-------|------|-----------|
| 0 | AppCall | `vote_dispute()` (triggers internal call) |
| 1 | Inner: Payment/AssetTransfer | Recipient: creator, Amount: `fee_total // 2`, Fee: 0 |
| 2 | Inner: Payment/AssetTransfer | Recipient: treasury, Amount: `fee_total - royalty`, Fee: 0 |
| 3 | Inner: Payment/AssetTransfer | Recipient: voted arbitrators, Amount: `fee_arbitration / voted_count` each, Fee: 0 |
| 4 | Inner: Payment/AssetTransfer | Recipient: creator, Amount: `remainder // 2`, Fee: 0 |
| 5 | Inner: Payment/AssetTransfer | Recipient: agent, Amount: `remainder // 2`, Fee: 0 |

**Note**: Index 1 (royalty) is a separate payment from index 4 (half of remainder). The creator receives two separate payments. This is intentional — royalty is a fixed 1% of escrow, while the half-split is 50% of the remaining balance.

---

### `timeout_dispute()`

**Action**: Split funds when dispute times out

**Transaction Group**: Same as `_execute_arbitration_payout(3)` — 6 inner payments (royalty, treasury, arbitrators, creator-half, agent-half).

---

### `auto_resolve_creator_win()`

**Action**: Auto-refund creator after 14-day dispute timeout

**Transaction Group**: Same as `resolve_dispute(creator_win)` — royalty omitted (dedup), 3 inner payments (treasury, mediator, creator).

---

### `claim_abandoned()`

**Action**: Refund creator after 3 rejections

**Transaction Group**: Same as `resolve_dispute(creator_win)` — royalty omitted (dedup), 3 inner payments (treasury, mediator, creator).
