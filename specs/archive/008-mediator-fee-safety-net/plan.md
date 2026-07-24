# Implementation Plan: Dynamic Mediator Fee Safety Net

**Branch**: `008-mediator-fee-safety-net` | **Date**: 2026-07-18 | **Spec**: [spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/008-mediator-fee-safety-net/spec.md)

---

## 1. Summary
This plan details the implementation of the Mediator Fee Safety Net (Constitution v2.1.0). The 0.25% mediator fee allocation will be dynamically routed to the worker when no mediation takes place (HITM mode or undisputed Auto mode), and split among mediators only when dispute resolution is triggered.

---

## 2. Technical Context
* **Language/Version**: Python 3.12, TypeScript (Next.js 16)
* **Primary Dependencies**: `py-algorand-sdk`, `@algorandfoundation/algokit-utils`
* **Storage**: PostgreSQL (Supabase) / SQLite (Local dev)
* **Testing**: `pytest`, Playwright E2E

---

## 3. Constitution Check
- [x] **Smart Contract Language**: Are all smart contracts written in Algorand Python and compiled via the Puya compiler? (AVM 12+)
- [x] **RekeyTo Protection**: Are all state-modifying contract methods protected by RekeyTo checks (`Txn.rekey_to() == Account(0)`)?
- [x] **Box Storage Limits**: Are keys and storage sizes inside boxes strictly limited?
- [x] **Karma Ledger Gatekeeping**: If the feature creates/claims, does it integrate with Karma?
- [x] **Escrow Funding Verification**: Does it implement dual-layer funding validation?
- [x] **Atomic Payout Group**: Are all payout/refund/splits atomic group transactions?
- [x] **OIDC Security**: Are GitHub automated tests validated securely?
- [x] **Database Compatibility**: Do DB operations support PostgreSQL and SQLite?
- [x] **Continuous Worker Setup**: Does the background indexer run continuously in a non-throttled GCP environment?
- [x] **Mediator Fee Safety Net**: Payouts redirect the 0.25% mediator fee to the worker if HITM is enabled or if Auto mode is undisputed.

---

## 4. Proposed Changes

### 4.1 Smart Contract
#### [MODIFY] [escrow.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/escrow.py)
* Refactor `_send_fee_split` to accept a boolean flag `is_dispute` or check contract state.
* If `self._get_is_hitm() == 1` or `not is_dispute`, transfer `fee_mediator` to the `primary_recipient` (the worker/claimant) instead of the mediator address.
* Update calls to `_send_fee_split` in `approve_work` (pass `is_dispute=False`) and `resolve_dispute` (pass `is_dispute=True`).

### 4.2 Gateway Backend API
#### [MODIFY] [bounties.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/gateway/routers/bounties.py)
* Update any fee calculation/estimation endpoints to mirror the contract's dynamic fee distribution rules.

### 4.3 Dashboard Frontend
#### [MODIFY] [useFeeBreakdown.ts](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/dashboard/src/hooks/useFeeBreakdown.ts)
* Update `computeFeeBreakdown` to set `mediator_fee = 0` and add that amount to `claimant_payout` when `hitmEnabled` is true, or when undisputed.

#### [MODIFY] [FeeBreakdownTable.tsx](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/dashboard/src/components/ui/FeeBreakdownTable.tsx)
* Add badge or tooltip explaining dynamic fee redirection.

---

## 5. Verification Plan

### Automated Tests
* Run unit tests to verify payout splits for HITM mode, undisputed Auto mode, and disputed Auto mode:
  `pytest tests/test_fee_safety_net.py`
