# Quickstart: Fee Split Display Validation

## Purpose

Verify that the fee split modal renders correctly before wallet signature on approve-payout flows.

## Prerequisites

- AlgoBounty dev environment running (`docker-compose up` or local gateway + dashboard)
- Local Algorand node (Algod) accessible
- Wallet configured in dashboard (KMD or external wallet)
- At least one bounty in `submitted` state with an escrow amount

## Scenario 1: Approve Payout with HITM

### Setup

1. Ensure a bounty exists in `submitted` state with an escrow amount ≥ 100 ALGO (easily visible fee breakdown)
2. Open the bounty detail page as the creator

### Test Steps

1. **Click "Approve & Release"** — the confirmation modal opens
2. **Verify fee breakdown table shows**:
   - Total Released: {escrow_amount} ALGO
   - Developer Royalty: {escrow * 2 // 100 // 2} ALGO (1%)
   - Platform Treasury: {escrow * 2 // 100 // 2} ALGO (1%)
   - Mediator Fee: {escrow * 25 // 10000} ALGO (0.25%)
   - Claimant Payout: {escrow - royalty - treasury - mediator} ALGO
3. **Click "Cancel"** — modal closes, no transaction sent
4. **Verify no transaction** was created on the blockchain (check algod logs or indexer)

### Expected Result

Modal shows exact fee split matching the contract's integer-division formula. Cancel action does nothing.

## Scenario 2: Approve Payout without HITM

### Setup

Use a non-HITM bounty (karma >= 10, no mediator required).

### Test Steps

1. Click "Approve & Release" on a non-HITM submitted bounty
2. **Verify**: Mediator Fee line is **absent** from the breakdown
3. **Verify**: Only Total, Royalty, Treasury, and Claimant Payout are shown

### Expected Result

Clean breakdown without mediator line. Royalty + Treasury = 2% of escrow. Claimant = rest.

## Scenario 3: Small Escrow (Edge Case)

### Setup

Use a bounty with escrow < 100 ALGO (where 1% rounds to 0 via integer division).

### Test Steps

1. Click "Approve & Release"
2. **Verify**: The modal still shows ALL lines, including Royalty and Treasury with `0.00` ALGO
3. **Verify**: Claimant payout = escrow amount (no fees deducted since they round to 0)

### Expected Result

Transparency maintained — user sees "Developer Royalty: 0.00" rather than a hidden/omitted line.

## Scenario 4: API Response Verification

### Test Steps

1. Open browser dev tools → Network tab
2. Click "Approve & Release"
3. **Verify** the `POST /api/bounties/{bounty_id}/get_approve_txn` response contains:
   - `unsigned_txn` (existing, base64-encoded)
   - `fee_breakdown` object with all fields
   - `fee_breakdown.display` with human-readable ALGO values

### Expected Result

Response body matches the contract in `contracts/api-get-approve-txn.md`.

## Manual Fee Calculation Reference

For verification, compute expected values:

```python
escrow = <value from bounty page in ALGO> * 1_000_000  # convert to micro-ALGO

# Core fees
royalty = treasury = escrow * 2 // 100 // 2  # 1% each
mediator = escrow * 25 // 10000 if hitm else 0  # 0.25%
claimant = escrow - royalty - treasury - mediator

# Verify conservation
assert claimant + royalty + treasury + mediator == escrow
```

If the displayed values don't match these computations, the implementation fails SC-002.
