# Data Model: Programmatic 50/50 Fee Split on Payouts

**Feature**: 006-fee-split-payouts

## Entity: Payout Fee Allocation

### Overview

This feature modifies the fee distribution logic in the escrow contract's payout paths. No new top-level entities are introduced; the change is a re-allocation of the existing 2% `treasury_fee` into two 1% sub-fees.

### Payout State Machine

```
State Transitions (unchanged):
  OPEN → CLAIMED → SUBMITTED → CLOSED (via approve_work / resolve_dispute / timeout / auto_release)
           ↓
         REJECTED → SUBMITTED (retry) or CLOSED (claim_abandoned)
      SUBMITTED → DISPUTED → CLOSED (vote_dispute / resolve_dispute / timeout)
```

**PAYOUT paths** (agent receives remaining balance):
- `approve_work()` → CLOSED, PAYOUT
- `_execute_arbitration_payout(1)` → CLOSED, PAYOUT
- `resolve_dispute("agent_win")` → CLOSED, PAYOUT
- `auto_release()` → CLOSED, PAYOUT

**REFUND paths** (creator receives remaining balance):
- `_execute_arbitration_payout(2)` → CLOSED, REFUND
- `resolve_dispute("creator_win")` → CLOSED, REFUND
- `auto_resolve_creator_win()` → CLOSED, REFUND
- `claim_abandoned()` → CLOSED, REFUND

**SPLIT paths** (creator + agent each receive half):
- `_execute_arbitration_payout(3)` → CLOSED, SPLIT
- `timeout_dispute()` → CLOSED, SPLIT

### Fee Allocation Model

#### Before (existing):

```
escrow_amount (e.g. 1,000 ALGO)
├── treasury_fee     = escrow_amount * 2 // 100       = 20 ALGO (2%)
├── mediator_fee     = escrow_amount * 25 // 10000    = 2.5 → 2 ALGO (0.25%, floor)
└── remainder        = escrow_amount - treasury - mediator
```

#### After (new):

```
escrow_amount (e.g. 1,000 ALGO)
├── fee_total        = escrow_amount * 2 // 100       = 20 ALGO (2%)
│   ├── royalty_fee  = fee_total // 2                  = 10 ALGO (1%) → creator
│   └── treasury_fee = fee_total - royalty_fee         = 10 ALGO (1%) → treasury
├── mediator_fee     = escrow_amount * 25 // 10000    = 2 ALGO (0.25%)
└── remainder        = escrow_amount - fee_total - mediator_fee
```

### Fee Split Table (1,000 ALGO example)

| Recipient | Before | After | Delta |
|-----------|--------|-------|-------|
| Creator Royalty | 0 | 10 ALGO | +10 |
| Treasury | 20 | 10 | -10 |
| Mediator | 2 | 2 | 0 |
| Agent (PAYOUT) | 978 | 978 | 0 |
| Creator (REFUND) | 978 | 978 | 0 |

**Note**: On PAYOUT paths, the agent payout amount is unchanged because the creator's new royalty payment comes from the treasury's 2% portion (which becomes 1% treasury). The total fee extracted from the escrow remains 2% + 0.25% = 2.25%.

### Micro-Payout Behavior (floor division)

| Escrow Amount | fee_total (2%) | royalty_fee (1%) | treasury_fee (1%) | Remainder for fee_total | Remainder for 0.25% fee |
|--------------|----------------|-------------------|--------------------|-------------------------|--------------------------|
| 100 ALGO | 2 | 1 | 1 | 0 | 0 |
| 200 ALGO | 4 | 2 | 2 | 0 | 0 |
| 150 ALGO | 3 | 1 | 2 | 1 | 0 |
| 1 ALGO | 0 | 0 | 0 | 0 | 0 |

Floor division means `royalty_fee` and `treasury_fee` may differ by 1 ALGO when `fee_total` is odd (the treasury absorbs the extra ALGO via `fee_total - royalty_fee`).

### Contract Box Fields (changes)

**No new box fields.** The `creator_address` box (already stored at `create_bounty()`) serves as the Developer Royalty destination.

| Box Key | Type | Role in Fee Split | Modified? |
|---------|------|-------------------|-----------|
| `creator_address` | Account | Recipient of 1% royalty fee | Read only (already exists) |
| `treasury_address` | Account | Recipient of 1% treasury fee | Read only (already exists) |
| `mediator_data.address` | Account | Recipient of 0.25% mediator fee | Read only (already exists) |
| `escrow_amount` | UInt64 | Base for fee calculation | Read only (already exists) |
| `asset_id` | UInt64 | Determines ALGO vs ASA transfer | Read only (already exists) |

## Validation Rules

1. **`fee_total = escrow_amount * 2 // 100`** — integer floor division, always ≥ 0
2. **`royalty_fee = fee_total // 2`** — floor division, always ≤ treasury_fee when `fee_total` is odd
3. **`treasury_fee = fee_total - royalty_fee`** — ensures royalty + treasury = fee_total exactly
4. **`mediator_fee = escrow_amount * 25 // 10000`** — unchanged from existing behavior
5. **`remainder = escrow_amount - fee_total - mediator_fee`** — remainder for primary recipient
6. **If `creator_address == primary_recipient`**: skip royalty payment (deduplication)
7. **Asset ID routing**: same `asset_id` used for all payment transactions in the group
