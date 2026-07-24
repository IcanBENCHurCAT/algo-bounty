# Implementation Plan: Programmatic 50/50 Fee Split on Payouts

**Branch**: `006-fee-split-payouts` | **Date**: 2026-07-16 | **Spec**: [link](./spec.md)

**Input**: Feature specification from `/specs/006-fee-split-payouts/spec.md`

## Summary

The escrow contract currently sends the full 2% platform fee to the treasury address in all payout and refund paths. This plan modifies the contract so that the 2% fee is programmatically split 50/50 on-chain: 1% (Developer Royalty) goes to the bounty creator's wallet address, and 1% (Platform Treasury) goes to the platform treasury account. The split is enforced via three-payment inner transactions in a single atomic group for PAYOUT paths, and a two-payment group for paths where the creator is the primary recipient.

## Technical Context

**Language/Version**: Python 3.x with Algorand Python (Puya) — compiles to AVM 12+ TEAL

**Primary Dependencies**:
- `algopy` — Algorand Python smart contract SDK
- `puya` — Algorand Python compiler targeting AVM 12+
- `py-algorand-sdk` — off-chain transaction construction and signing

**Storage**: Box-based persistent state within the app account. Existing boxes: `treasury_address`, `creator_address`, `escrow_amount`, `asset_id`, `payout_type`, `state`, `mediator_data`, `agent_address`, plus 20+ others.

**Testing**: `pytest` with `py-algorand-sdk` for unit and integration tests. Existing tests live under `tests/`. Performance benchmarks exist in `test_perf.py`, `test_perf_1000.py`.

**Target Platform**: Algorand mainnet (target deployment), testnet for staging.

**Project Type**: Smart contract (AVM) + FastAPI gateway backend.

**Performance Goals**: Contract must fit within AVM opcode and execution limits. Adding two inner payments increases the approved payment count by 2 in the approval program. Payout paths add ~20–40 opcodes per flow.

**Constraints**:
- All inner payment transactions must use `fee=0` (paid by sender).
- The atomic group validation (FR-04) must verify total amounts sum exactly.
- Floor division is acceptable for sub-ALGO remainders.
- RekeyTo protection already present on all state-modifying methods.
- Box storage must not exceed existing limits (Proof URL ≤ 512, Proof JSON ≤ 2048, Dispute Reason ≤ 256). Adding one Account box (`developer_royalty_address`) adds negligible overhead.

**Scale/Scope**: All ~9 payout/refund code paths in the escrow contract must be modified. No new API endpoints or database changes required beyond the contract upgrade.

## Constitution Check

- [x] **Smart Contract Language**: Algorand Python (Puya), compiles to AVM 12+ TEAL. (Rule 2.1)
- [x] **RekeyTo Protection**: All 13 state-modifying methods already contain `Txn.rekey_to == Account(0)` assertions. No new state-modifying method is introduced.
- [x] **Box Storage Limits**: Adding one `developer_royalty_address` Account box. No Proof URL, Proof JSON, or Dispute Reason changes.
- [x] **Karma Ledger Gatekeeping**: This feature does not create or claim bounties; it modifies payout distributions only.
- [x] **Escrow Funding Verification**: This feature does not modify escrow creation or funding logic. The existing `_verify_escrow_funding` and `_verify_escrow_balance` remain unchanged.
- [x] **Atomic Payout Group**: All payout paths already use `itxn.Payment` / `itxn.AssetTransfer` with `fee=0`. This feature adds inner payments within the same app call — each path remains a single app call producing multiple inner payments, which is the canonical atomic pattern. (Rule 10.3)
- [x] **OIDC Security**: This feature does not alter OIDC token handling in `github_verify`.
- [x] **Database Compatibility**: No database changes. The gateway payout orchestration is updated to pass the developer royalty address.
- [x] **Continuous Worker Setup**: No changes to the background worker/indexer.

**GATE**: All checks pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/006-fee-split-payouts/
├── plan.md              # This file
├── research.md          # Phase 0 output (inline below — no open questions)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
escrow.py                    # Main smart contract — modify payout paths
EscrowContract.approval.teal # Compiled output (auto-generated)
tests/test_escrow.py         # Unit/integration tests — add fee-split tests
gateway/                     # Off-chain payout orchestration — update caller
tests/                       # Existing test suite
```

**Structure Decision**: Single-project modification. The feature touches one smart contract file (`escrow.py`) and the payout orchestration in the gateway layer. No new top-level directories or modules needed.

## Phase 0: Research

**No open NEEDS CLARIFICATION items remain.** The specification was fully resolved with informed defaults based on the existing contract and Constitution Section 5.3.

**Research Decision 1 — Fee split applies to PAYOUT paths only.**

- Rationale: Constitution Section 5.3 defines "Developer Royalty" as compensation to the creator. On PAYOUT paths (agent_win), the creator is not receiving funds — the agent is. Paying the creator their royalty share makes the effective agent payout 98% and gives the creator 1% as platform stewardship compensation. On REFUND paths (creator_win), the creator is receiving the full remaining balance, so paying them "royalty" on top would overpay. The split only modifies the fee allocation in REFUND paths as a bookkeeping normalization (treasury still receives 1%, creator still receives 99%).
- Alternative considered: Apply the 50/50 split uniformly to all paths that extract the 2% fee. This was rejected as it creates inconsistent semantics — the creator would receive "royalty" from their own refund.
- Decision: Apply the 50/50 fee split consistently to ALL paths that currently send the 2% fee to treasury. On PAYOUT paths (agent_win, auto_release), this means a new payment to the creator's address. On REFUND paths (creator_win, abandoned_refund), the "developer royalty" payment is already going to the creator, so the logic is reorganized to split the fee first, then pay the creator the remaining balance. This ensures the 2% fee extraction is always: 1% royalty to creator, 1% treasury, rest to recipient.

**Research Decision 2 — Fee split is hardcoded 50/50, not configurable at contract level.**

- Rationale: Constitution Section 5.3 states the split is "50% of collected fees (i.e., 1% of total payout)". Making it configurable at contract level would add complexity and a new Box. If future governance requires a different ratio, a new contract deployment (or upgrade via proxy) is appropriate and required by Constitution 5.4.
- Alternative considered: Store `royalty_ratio` as a configurable Box field. Rejected as premature — the constitution fixes the ratio, and any future change requires the full spec-kit process.

## Phase 1: Design

### Data Model Changes

The contract requires one new box field:

| Box Key | Type | Purpose | Default |
|---------|------|---------|---------|
| `developer_royalty_address` | `Account` | Wallet address of the bounty creator (receipt of 1% royalty) | Set at `create_bounty()` to `Txn.sender` |

The `creator_address` box already exists. The `developer_royalty_address` can be initialized from the same `Txn.sender` value used for `creator_address` at bounty creation time, or the royalty address can simply be the creator address (eliminating the need for a separate box entirely — see implementation note below).

**Implementation Optimization**: Since the Developer Royalty address is the bounty creator's address (already stored in `creator_address`), adding a separate `developer_royalty_address` box is redundant. The implementation will use `self.creator_address.value` directly as the royalty destination. This avoids any new box storage overhead and keeps the change minimal. The Constitution Section 5.3 already defines the royalty as going "to the creator's wallet address."

### Payout Path Impact Matrix

| Method | Current State | Current Fee Recipients | New Fee Recipients | New Recipient Count |
|--------|--------------|----------------------|-------------------|---------------------|
| `approve_work()` | CLOSED | treasury (2%) | royalty + treasury (1% + 1%) | +1 payment |
| `_execute_arbitration_payout(agent_win)` | CLOSED | treasury (2%) | royalty + treasury (1% + 1%) | +1 payment |
| `resolve_dispute(agent_win)` | CLOSED | treasury + mediator (2% + 0.25%) | royalty + treasury + mediator (1% + 1% + 0.25%) | +1 payment |
| `auto_release()` | CLOSED | treasury (2%) | royalty + treasury (1% + 1%) | +1 payment |
| `resolve_dispute(creator_win)` | CLOSED | treasury + mediator (2% + 0.25%) | royalty + treasury + mediator (1% + 1% + 0.25%) | +1 payment (but royalty=creator, so same address) |
| `auto_resolve_creator_win()` | CLOSED | treasury (2%) | royalty + treasury (1% + 1%) | +1 payment (but royalty=creator, so same address) |
| `timeout_dispute()` | CLOSED | treasury + mediator (2% + 0.25%) | royalty + treasury + mediator (1% + 1% + 0.25%) | +1 payment (royalty=creator, split with agent) |
| `claim_abandoned()` | CLOSED | treasury + mediator (2% + 0.25%) | royalty + treasury + mediator (1% + 1% + 0.25%) | +1 payment (but royalty=creator, so same address) |

**Key observation**: For all paths where the refund recipient IS the creator, the "developer royalty" payment goes to the same address as the primary refund. The implementation can either:
1. Always emit the royalty payment (producing duplicate payments to the same address — wasteful but correct), or
2. Check if the royalty address equals the primary recipient and skip the royalty payment in that case.

**Decision**: Option 2 — skip the royalty payment when the royalty address equals the primary recipient. This minimizes gas and avoids confusing duplicate transactions. A helper method `_send_fee_split()` will handle this.

### Contract Change: `approve_work()` example

Before:
```python
fee_treasury = escrow_amount * 2 // 100
fee_mediator = escrow_amount * 25 // 10000
remaining_amount = escrow_amount - fee_treasury - fee_mediator

self._send_payout(self.treasury_address.value, fee_treasury, asset_id)
self._send_payout(Account(self.mediator_data.value.address.bytes), fee_mediator, asset_id)
self._send_payout(self._get_agent_address(), remaining_amount, asset_id)
```

After:
```python
fee_total = escrow_amount * 2 // 100          # 2% total fee
fee_royalty = fee_total // 2                   # 1% to creator
fee_treasury = fee_total - fee_royalty         # 1% to treasury (same when fee_total is even)
fee_mediator = escrow_amount * 25 // 10000     # 0.25% mediator (unchanged)
remaining_amount = escrow_amount - fee_total - fee_mediator

self._send_payout(self.creator_address.value, fee_royalty, asset_id)
self._send_payout(self.treasury_address.value, fee_treasury, asset_id)
self._send_payout(Account(self.mediator_data.value.address.bytes), fee_mediator, asset_id)
self._send_payout(self._get_agent_address(), remaining_amount, asset_id)
```

### Helper Method: `_send_fee_split()`

A new private method to reduce duplication across all 8 payout/refund paths:

```python
def _send_fee_split(self, recipient: Account, escrow_amount: UInt64, asset_id: UInt64, mediator: Account) -> UInt64:
    """
    Split the 2% platform fee: 1% royalty to creator, 1% to treasury.
    Pay the mediator fee separately.
    Returns the amount available for the primary recipient after all fees.
    """
    fee_total = escrow_amount * 2 // 100
    fee_royalty = fee_total // 2
    fee_treasury = fee_total - fee_royalty
    fee_mediator = escrow_amount * 25 // 10000
    
    # Developer royalty (1% to creator)
    if self.creator_address.value != recipient:
        self._send_payout(self.creator_address.value, fee_royalty, asset_id)
    
    # Platform treasury (1% to treasury)
    self._send_payout(self.treasury_address.value, fee_treasury, asset_id)
    
    # Mediator fee (0.25% — unchanged from existing behavior)
    self._send_payout(mediator, fee_mediator, asset_id)
    
    return escrow_amount - fee_total - fee_mediator
```

### Off-Chain Gateway Changes

The gateway payout orchestration (in `gateway/`) must be updated to:
1. Read the developer royalty address from the escrow box data (`creator_address`) — this is already available.
2. Construct the atomic transaction group with the correct number of inner payments per path (4 payments for PAYOUT paths, 3 for some refund paths where royalty=creator).
3. The contract now enforces the split on-chain, so the gateway only needs to match the expected amounts. No additional address validation beyond what's already in place is needed.

### Re-evaluated Constitution Check (post-design)

All 9 gates pass. The design uses only existing boxes (`creator_address` as royalty destination). No new state is introduced. All payout paths remain within AVM limits.

## Complexity Tracking

No Constitution violations require justification.
