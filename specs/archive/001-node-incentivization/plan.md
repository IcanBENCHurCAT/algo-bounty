# Implementation Plan: Node Incentivization & Fee Splitting

**Branch**: `001-node-incentivization` | **Date**: 2026-07-19 | **Spec**: [spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/001-node-incentivization/spec.md)

## Summary

This feature implements a decentralized incentivization model for AlgoBounty federated gateway nodes. By allowing gateway nodes to register their address during bounty creation, we route 0.5% of the total bounty payout (half of the standard 1% Platform Treasury fee) to the node operator. If no gateway address is provided, the full 1% platform fee goes to the central treasury.

We will achieve this by:
1. Adding a new `gateway_address` storage box to `escrow.py`.
2. Modifying the `create_bounty` ABI method signature to accept `gateway_address: Account` directly:
   `create_bounty(byte[],uint64,uint64,uint64,uint64,address,address,address)void`
3. Updating `_send_fee_split` to divide the platform treasury fee when `gateway_address` is set and is not the zero address.
4. Adding `gateway_address` column to database and API models.

---

## User Review Required

> [!NOTE]
> Based on user feedback, we are directly modifying the ABI signature of `create_bounty` to include the `gateway_address` parameter, rather than preserving backward compatibility. All backend routes and test transaction calls will be updated to match the new signature.

---

## Open Questions

None.

---

## Proposed Changes

### Smart Contract

#### [MODIFY] [escrow.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/escrow.py)
- Define `self.gateway_address = Box(Account, key="gateway_address")` inside `EscrowContract.__init__`.
- Update `create_bounty` method signature and logic:
  - Add `gateway_address: Account` parameter.
  - Store `self.gateway_address.value = gateway_address`.
- Update `_send_fee_split` helper:
  - Calculate `fee_platform` as usual (2% total: 1% developer royalty + 1% treasury).
  - If `gateway_address` is set and is not the zero address:
    - Route 0.5% (`fee_platform // 4` of the 2% fee) to `gateway_address`.
    - Route 0.5% (`fee_platform - (fee_platform // 4)`) to `treasury_address`.
  - Otherwise, route full 1% to `treasury_address`.
  - Send 1% to `creator_address` (developer royalty).

---

### Backend Gateway

#### [MODIFY] [supabase_migration.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/gateway/supabase_migration.py)
- Add `gateway_address = Column(String(58), nullable=True)` to the `Bounty` model.

#### [MODIFY] [schemas.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/gateway/schemas.py)
- Add `gateway_address: Optional[str] = None` to `BountyCreate` and `BountyResponse`.

#### [MODIFY] [routers/bounties.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/gateway/routers/bounties.py)
- Update signature parser and save `gateway_address` in database when creating a bounty.

---

## Constitution Check

- [x] **Smart Contract Language**: Written in Algorand Python (Puya) and compiled via `compile_teal.py`.
- [x] **RekeyTo Protection**: Method `create_bounty` continues to enforce no rekeying.
- [x] **Box Storage Limits**: `gateway_address` box size is exactly 32 bytes (well under the limit).
- [x] **Atomic Payout Group**: Payout logic continues to use atomic transaction groups.
- [x] **Database Compatibility**: Model changes are fully compatible with both PostgreSQL and local SQLite.
- [x] **Mediator Fee Safety Net**: Safe net rules (refunding 0.25% mediator fee under HITM or undisputed Auto modes) are preserved.

---

## Verification Plan

### Automated Tests
- Build and run unit tests for the smart contract: `PYTHONPATH=. python -m pytest tests/`
- Specifically, update existing tests to pass `gateway_address` (or a zero address placeholder) to `create_bounty`.
