# Tasks: Programmatic 50/50 Fee Split on Payouts

**Input**: Design documents from `/specs/006-fee-split-payouts/`

**Prerequisites**: plan.md (tech stack, libraries, structure), spec.md (user stories), data-model.md, contracts/, quickstart.md

**Branch**: `006-fee-split-payouts`

**Tests**: Test tasks included. Write tests FIRST, ensure they FAIL before implementation.

---

## Summary

This feature modifies all ~8 payout/refund code paths in the AlgoBounty escrow smart contract to split the 2% platform fee 50/50 on-chain: 1% (Developer Royalty) goes to the bounty creator's wallet address, and 1% (Platform Treasury) goes to the platform treasury account. The split is enforced via inner payment transactions within each app call, with a deduplication check that skips the royalty payment when the creator is the primary refund recipient.

**Single user story** with one comprehensive implementation scope — all payout paths are part of the same revenue-sharing mechanism (Constitution Section 5.3).

## User Story

- **US1**: Programmatic 50/50 Fee Split on Payouts (Priority: P1)

## Path Impact Map

| Method | Payout Type | New Payments | Royalty Dedup? |
|--------|-------------|-------------|----------------|
| `approve_work()` | PAYOUT | +royalty | No — agent receives remainder |
| `_execute_arbitration_payout(1)` | PAYOUT | +royalty | No — agent receives remainder |
| `_execute_arbitration_payout(2)` | REFUND | treasury only | Yes — creator = refund recipient |
| `resolve_dispute("agent_win")` | PAYOUT | +royalty | No — agent receives remainder |
| `resolve_dispute("creator_win")` | REFUND | treasury only | Yes — creator = refund recipient |
| `auto_release()` | PAYOUT | +royalty | No — agent receives remainder |
| `auto_resolve_creator_win()` | REFUND | treasury only | Yes — creator = refund recipient |
| `timeout_dispute()` | SPLIT | +royalty | No — creator receives half of remainder |
| `claim_abandoned()` | REFUND | treasury only | Yes — creator = refund recipient |

## Dependencies & Execution Order

- **Phase 1**: No dependencies — can start immediately
- **Phase 2**: Depends on Phase 1 — BLOCKS all user story work
- **Phase 3 (US1)**: Depends on Phase 2 completion — single story, all payout paths
- **Phase 4**: Depends on Phase 3 — cross-cutting polish

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Branch, compilation, and baseline verification

- [ ] T001 Ensure working on branch `006-fee-split-payouts` (already created)
- [ ] T002 Verify compilation: `python compile_teal.py` — confirm `EscrowContract.approval.teal` and `clear.teal` generated without errors
- [ ] T003 Run existing test suite baseline: `python -m pytest tests/ -v` — confirm all tests pass before changes (establishes baseline confidence)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the helper method and understand every payout path

**⚠️ CRITICAL**: All payout path modifications (Phase 3) depend on the helper method being correct.

- [ ] T004 Implement `_send_fee_split()` helper in `escrow.py` — the core fee-splitting logic:
  - Computes `fee_total = escrow_amount * 2 // 100`
  - Computes `fee_royalty = fee_total // 2` (1% to creator, floored)
  - Computes `fee_treasury = fee_total - fee_royalty` (1% to treasury, absorbs odd remainder)
  - Computes `fee_mediator = escrow_amount * 25 // 10000` (0.25%, unchanged)
  - If `creator_address != recipient`: emit royalty payment via `_send_payout()`
  - Always emit treasury payment via `_send_payout()`
  - Always emit mediator payment via `_send_payout()`
  - Returns `remaining_amount = escrow_amount - fee_total - fee_mediator`
  - All payments use `fee=0` and the correct `asset_id` (ALGO or ASA)

---

## Phase 3: User Story 1 — Programmatic 50/50 Fee Split on Payouts (Priority: P1) 🎯

**Goal**: Modify all 8 payout/refund code paths in `escrow.py` to call `_send_fee_split()` instead of the current single-treasury fee extraction, and emit the correct number of inner payment transactions per path.

**Independent Test**: A single escrow can be funded, claimed, submitted, and approved. The payout verifies 4 inner payments (royalty, treasury, mediator, agent) with correct amounts summing to the escrow balance.

### Tests for User Story 1

- [ ] T005 [P] [US1] Unit test: `approve_work()` emits 4 inner payments with correct amounts (royalty=1%, treasury=1%, mediator=0.25%, agent=remainder) in `tests/test_fee_split_payout.py`
- [ ] T006 [P] [US1] Unit test: `approve_work()` with 100 ALGO escrow verifies floor division (royalty=1, treasury=1, mediator=2, agent=96) in `tests/test_fee_split_payout.py`
- [ ] T007 [P] [US1] Unit test: `auto_release()` emits same 4-payment structure as `approve_work()` in `tests/test_fee_split_payout.py`
- [ ] T008 [P] [US1] Unit test: `_execute_arbitration_payout(agent_win=1)` emits 4 payments including royalty to creator in `tests/test_fee_split_payout.py`
- [ ] T009 [P] [US1] Unit test: `_execute_arbitration_payout(creator_win=2)` emits 3 payments (royalty deduped, only treasury + mediator + creator) in `tests/test_fee_split_payout.py`
- [ ] T010 [P] [US1] Unit test: `resolve_dispute("agent_win")` emits 4 payments in `tests/test_fee_split_payout.py`
- [ ] T011 [P] [US1] Unit test: `resolve_dispute("creator_win")` emits 3 payments (royalty deduped) in `tests/test_fee_split_payout.py`
- [ ] T012 [P] [US1] Unit test: `timeout_dispute()` emits 6 payments (royalty, treasury, arbitrators, creator-half, agent-half) in `tests/test_fee_split_payout.py`
- [ ] T013 [P] [US1] Unit test: `auto_resolve_creator_win()` emits 3 payments (royalty deduped) in `tests/test_fee_split_payout.py`
- [ ] T014 [P] [US1] Unit test: `claim_abandoned()` emits 3 payments (royalty deduped) in `tests/test_fee_split_payout.py`
- [ ] T015 [P] [US1] Unit test: ASA escrow (non-ALGO asset) payout emits correct fee split using ASA transfer instead of ALGO payment in `tests/test_fee_split_payout.py`
- [ ] T016 [P] [US1] Unit test: Micro-payout of 1 ALGO (fee_total=0, all fees=0) — edge case in `tests/test_fee_split_payout.py`
- [ ] T017 [P] [US1] Integration test: Full lifecycle — create bounty, fund escrow, claim, submit work, approve, verify all 4 payments in `tests/test_fee_split_integration.py`

### Implementation for User Story 1

- [ ] T018 [US1] Modify `approve_work()` in `escrow.py`:
  - Replace: `fee_treasury = escrow_amount * 2 // 100` and single treasury payment
  - With: `remaining_amount = self._send_fee_split(self._get_agent_address(), escrow_amount, asset_id, mediator_address)`
  - Then emit the remaining_amount payment to the agent (the helper already emits royalty, treasury, and mediator)
  - Keep existing `_verify_escrow_balance`, `payout_type`, state change, and log intact

- [ ] T019 [US1] Modify `_execute_arbitration_payout()` in `escrow.py`:
  - For consensus=1 (agent_win): replace treasury payment with `_send_fee_split(agent_address, ...)` which emits royalty + treasury + mediator, then emit remaining_amount to agent
  - For consensus=2 (creator_win): replace treasury payment with `_send_fee_split(creator_address, ...)` which dedups royalty, emits only treasury + mediator, then emit remaining_amount to creator
  - For consensus=3 (split): same pattern — _send_fee_split splits the fee, then emit half_amount to creator and half_amount to agent
  - Arbitrator payments (fee_per_arbitrator) remain unchanged — they come from the 5% arbitration fee pool, not the 2% platform fee

- [ ] T020 [US1] Modify `resolve_dispute()` in `escrow.py`:
  - For "agent_win": replace treasury payment with `_send_fee_split(agent_address, escrow_amount, asset_id, mediator_address)`, then emit remaining_amount to agent
  - For "creator_win": replace treasury payment with `_send_fee_split(creator_address, escrow_amount, asset_id, mediator_address)`, then emit remaining_amount to creator (royalty deduped)

- [ ] T021 [US1] Modify `auto_release()` in `escrow.py`:
  - Replace treasury payment with `_send_fee_split(agent_address, escrow_amount, asset_id, mediator_address)`
  - Then emit remaining_amount to agent

- [ ] T022 [US1] Modify `auto_resolve_creator_win()` in `escrow.py`:
  - Replace treasury payment with `_send_fee_split(creator_address, escrow_amount, asset_id, Account(0))` — mediator fee=0 since no mediator involved
  - Then emit remaining_amount to creator

- [ ] T023 [US1] Modify `timeout_dispute()` in `escrow.py`:
  - Replace treasury payment with `_send_fee_split(...)` with mediator
  - Then emit half_amount to creator and half_amount to agent

- [ ] T024 [US1] Modify `claim_abandoned()` in `escrow.py`:
  - Replace treasury payment with `_send_fee_split(creator_address, escrow_amount, asset_id, mediator_address)`
  - Then emit remaining_amount to creator (royalty deduped)

- [ ] T025 [US1] Re-compile and verify: `python compile_teal.py` — ensure no compilation errors
- [ ] T026 [US1] Re-run baseline tests: `python -m pytest tests/ -v` — confirm all existing tests still pass

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Quality assurance, validation, and documentation

- [ ] T027 [P] Run full validation suite from `quickstart.md`: `python -m pytest tests/test_fee_split_payout.py tests/test_fee_split_integration.py -v`
- [ ] T028 [P] Verify AVM opcode limits: check that `EscrowContract.approval.teal` compiled size is within limits (no bytecode bloat from new inner payments)
- [ ] T029 [P] Verify Constitution compliance: all state-modifying methods still have `Txn.rekey_to == Account(0)` check (no accidental removals during refactoring)
- [ ] T030 [P] Verify box storage limits unchanged: no new boxes beyond `creator_address` (which was already present)
- [ ] T031 [P] Run performance benchmarks: `python test_perf.py` and `python test_perf_1000.py` — verify no significant performance regression from additional inner payments
- [ ] T032 [P] Update `README.md` — document the new fee split behavior in the payout section
- [ ] T033 [P] Commit all changes with descriptive message: `git add -A && git commit -m "feat: implement 50/50 fee split on all payout paths"`
- [ ] T034 [P] Verify git diff is clean except for `escrow.py`, `EscrowContract.*.teal`, `EscrowContract.arc56.json`, and new test files

---

## Parallel Execution Example: User Story 1

```bash
# Launch all test tasks in parallel (tests are independent):
Task: "Unit test for approve_work()"
Task: "Unit test for auto_release()"
Task: "Unit test for _execute_arbitration_payout(agent_win)"
Task: "Unit test for _execute_arbitration_payout(creator_win)"
Task: "Unit test for resolve_dispute(agent_win)"
Task: "Unit test for resolve_dispute(creator_win)"
Task: "Unit test for timeout_dispute()"
Task: "Unit test for auto_resolve_creator_win()"
Task: "Unit test for claim_abandoned()"
Task: "Unit test for ASA escrow payout"
Task: "Unit test for micro-payout edge case"
Task: "Integration test: full lifecycle"

# After tests fail (expected), implement payout paths in parallel:
Task: "Modify approve_work() in escrow.py"
Task: "Modify _execute_arbitration_payout() in escrow.py"
Task: "Modify resolve_dispute() in escrow.py"
Task: "Modify auto_release() in escrow.py"
Task: "Modify auto_resolve_creator_win() in escrow.py"
Task: "Modify timeout_dispute() in escrow.py"
Task: "Modify claim_abandoned() in escrow.py"
```

---

## Implementation Strategy

### MVP First (US1 Complete)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational — create `_send_fee_split()` helper (T004)
3. Complete Phase 3: US1 — implement all 8 payout path modifications + tests (T005-T026)
4. STOP and VALIDATE: run `python -m pytest tests/ -v` — all tests pass
5. Deploy/verify on sandbox

### Incremental Delivery

1. Phase 1+2 → Foundation ready
2. Phase 3 → MVP: all payout paths modified, all tests pass
3. Phase 4 → Polish: performance verification, constitution compliance, documentation

---

## Notes

- All payout paths share the same `_send_payout()` helper (which handles ALGO vs ASA routing). The only change is injecting the royalty payment before the treasury payment.
- The `_send_fee_split()` helper returns `remaining_amount`, which each calling method then emits to the primary recipient (agent, creator, or creator/agent split).
- Deduplication is handled inside `_send_fee_split()`: `if self.creator_address.value != recipient: emit_royalty()`. This is the single source of truth for the dedup rule.
- Mediator fee extraction is preserved unchanged — all existing paths already pass the mediator address.
- Arbitrator payments (from the 5% arbitration fee pool) are unaffected by this feature.
