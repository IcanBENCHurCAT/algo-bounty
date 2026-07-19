# Data Model: Platform Fee Splits Pre-Signed Validation

## Entities

### FeeBreakdown

Computed fee split for a single escrow payout. Mirrors the on-chain integer-division logic from `escrow.py._send_fee_split()`.

| Field | Type | Description |
|-------|------|-------------|
| `escrow_amount` | `int` | Total escrow in micro-ALGO (raw contract value) |
| `royalty` | `int` | Developer royalty in micro-ALGO: `escrow * 2 // 100 // 2` |
| `treasury` | `int` | Platform treasury in micro-ALGO: `escrow * 2 // 100 // 2` |
| `mediator` | `int` | Mediator fee in micro-ALGO: `escrow * 25 // 10000` (0 if HITM disabled) |
| `arbitrator` | `int` | Arbitrator fee in micro-ALGO (only for dispute SPLIT/REFUND) |
| `claimant` | `int` | Recipient payout: `escrow - royalty - treasury - mediator - arbitrator` |
| `hitm_enabled` | `bool` | Whether mediator fee applies |
| `payout_type` | `str` | `PAYOUT` | `REFUND` | `SPLIT` — determines fee applicability |

**Invariants**:
- `royalty == treasury` always (50/50 split of the 2% platform fee)
- `claimant + royalty + treasury + mediator (+ arbitrator) == escrow_amount` (total is conserved)
- All values are non-negative
- Values use ALGO for display (divide by 1_000_000) but micro-ALGO for computation

### FeeBreakdownDisplay

Frontend-usable, human-readable representation.

| Field | Type | Description |
|-------|------|-------------|
| `escrow_algo` | `str` | Escrow in ALGO (e.g. `"1000.00"` or `"0.50"`) |
| `royalty_algo` | `str` | Royalty in ALGO (e.g. `"10.00"`) |
| `treasury_algo` | `str` | Treasury in ALGO (e.g. `"10.00"`) |
| `mediator_algo` | `str \| null` | Mediator in ALGO, or `null` if HITM disabled |
| `arbitrator_algo` | `str \| null` | Arbitrator in ALGO, or `null` if not applicable |
| `claimant_algo` | `str` | Claimant payout in ALGO |
| `mediator_visible` | `bool` | Whether mediator fee line should render |
| `arbitrator_visible` | `bool` | Whether arbitrator fee line should render |
| `refund_mode` | `bool` | If true, show "No fees deducted — full refund" |

**Formatting rules** (FR-010):
- If value is a whole number: `"1000"` (no decimal)
- If value has fractional ALGO: `"0.50"` (2 decimal places)
- Never display raw micro-ALGO to the user

### ApprovalModalState

UI state for the approve-payout modal.

| Field | Type | Description |
|-------|------|-------------|
| `isOpen` | `boolean` | Modal visibility |
| `bountyId` | `string` | Bounty ID being approved |
| `feeBreakdown` | `FeeBreakdownDisplay` | Pre-computed fee breakdown from API |
| `unsignedTxn` | `object` | Transaction group object from gateway |
| `status` | `'idle' | 'loading' | 'ready' | 'signing' | 'done'` | Modal step state |
| `error` | `string \| null` | Error message if applicable |

### DisputeResolutionModalState

UI state for dispute resolution modal. Extends ApprovalModalState with dispute-specific fields.

| Field | Type | Description |
|-------|------|-------------|
| `resolutionType` | `str` | `PAYOUT` | `REFUND` | `SPLIT` |
| `mediatorAddress` | `str \| null` | Mediator address (if HITM) |
| `arbitratorAddress` | `str \| null` | Arbitrator address (if arbitration) |
| `splitPercentCreator` | `int \| null` | Percentage to creator (for SPLIT type) |
| `splitPercentAgent` | `int \| null` | Percentage to agent (for SPLIT type) |

## Relationships

```
Bounty (existing) ──┬──► FeeBreakdown (computed on demand, not stored)
                    │
                    ├──► ApprovalModalState (frontend-only, transient)
                    │
                    └──► DisputeResolutionModalState (frontend-only, transient)

getApproveTxn (API) ──► returns { unsigned_txn, fee_breakdown }
                        fee_breakdown contains both raw micro-ALGO and display-formatted values
```

## Key Computations

The `fee_breakdown` must be computed identically on both backend and frontend:

```python
# Backend computation (gateway/bounty routes)
royalty = treasury = escrow_amount * 2 // 100 // 2
mediator = escrow_amount * 25 // 10000 if hitm_enabled else 0
claimant = escrow_amount - royalty - treasury - mediator
```

Dispute-specific additions:

```python
# For SPLIT or REFUND resolution types
arbitrator_fee = escrow_amount * 50 // 10000 if dispute_resolved else 0
claimant_after_arbitrator = claimant - arbitrator_fee
```
