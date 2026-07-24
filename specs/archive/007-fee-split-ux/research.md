# Research: Platform Fee Splits Pre-Signed Validation

## Findings

No research required. This feature has zero technical unknowns.

## Decisions

| Decision | Rationale |
|----------|-----------|
| No smart contract changes | The `_send_fee_split()` helper from #006 already handles fee routing on-chain. We only add UI visibility. |
| Extend `get_approve_txn` endpoint | Minimal change — add a `fee_breakdown` dict to the existing response rather than creating a new endpoint. |
| Client-side fee computation also needed | The frontend needs a `useFeeBreakdown` hook for client-side validation that matches the contract's integer-division logic, as a defense-in-depth measure (SC-002). |
| Use same modal pattern as existing flows | Dashboard already has modal/dialog components for disputes and wallet interactions. Reuse that pattern. |

## No Unknowns

- Contract fee formula: Already known from #006 contract implementation
- API structure: Existing `get_approve_txn` endpoint is documented in gateway code
- Frontend modal patterns: Already exist for dispute flows and wallet connections
- Fee calculation: Simple integer arithmetic, same logic on both sides
