# API Contract: Extended `get_approve_txn` Response

## Endpoint

```
POST /api/bounties/{bounty_id}/get_approve_txn
Authorization: Bearer {jwt}
```

## Response Schema (Extended)

### Before (existing)

```json
{
  "unsigned_txn": "base64-encoded-msgpack"
}
```

### After (feature #007)

```json
{
  "unsigned_txn": "base64-encoded-msgpack",
  "fee_breakdown": {
    "escrow_amount": 1000000000,
    "royalty": 1000000,
    "treasury": 1000000,
    "mediator": 250000,
    "claimant": 996250000,
    "hitm_enabled": true,
    "payout_type": "PAYOUT",
    "display": {
      "escrow_algo": "1000.00",
      "royalty_algo": "1.00",
      "treasury_algo": "1.00",
      "mediator_algo": "0.25",
      "claimant_algo": "996.25"
    }
  }
}
```

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `unsigned_txn` | `string` | Existing field — base64-encoded msgpack of the `ApplicationNoOpTxn` |
| `fee_breakdown` | `object` | NEW — computed fee split for the approval |
| `fee_breakdown.escrow_amount` | `int` | Escrow in micro-ALGO (raw from box storage) |
| `fee_breakdown.royalty` | `int` | Developer royalty in micro-ALGO |
| `fee_breakdown.treasury` | `int` | Platform treasury in micro-ALGO |
| `fee_breakdown.mediator` | `int` | Mediator fee in micro-ALGO (0 if HITM disabled) |
| `fee_breakdown.claimant` | `int` | Recipient payout: `escrow - royalty - treasury - mediator` |
| `fee_breakdown.hitm_enabled` | `bool` | Whether the bounty is HITM-enabled |
| `fee_breakdown.payout_type` | `str` | Always `PAYOUT` for approve flow |
| `fee_breakdown.display.*` | `str` | Human-readable ALGO values (2 decimal places for <1 ALGO, whole numbers otherwise) |

## Computation Formula

The backend MUST compute fees using the same integer-division floor as the contract:

```python
royalty = treasury = escrow_amount * 2 // 100 // 2
mediator = escrow_amount * 25 // 10000 if hitm_enabled else 0
claimant = escrow_amount - royalty - treasury - mediator
```

## Frontend Integration

The frontend `getApproveTxn` call (from `dashboard/src/lib/api.ts`) will now receive an additional `fee_breakdown` field. The approval modal component should:

1. Call `getApproveTxn`
2. If `fee_breakdown` is present, render the fee breakdown table
3. Require user to click "Confirm & Sign" before proceeding to wallet signature
4. Pass the same `unsigned_txn` to `approveWork` (unchanged)

## Error Responses (unchanged)

| Status | Detail |
|--------|--------|
| 404 | `"Bounty not found"` |
| 400 | `"Bounty has no deployed smart contract application ID."` |
| 403 | `"Only creator can approve work"` |
| 400 | `"Bounty has no work submitted to approve"` |
