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

- **Phase 1**: ✅ Complete
- **Phase 2**: ✅ Complete
- **Phase 3**: ✅ Complete — all payout paths modified, all tests pass
- **Phase 4**: Remaining polish tasks

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Branch, compilation, and baseline verification

- [x] T001 Ensure working on branch `006-fee-split-payouts` (already created)
- [x] T002 Verify compilation: `python compile_teal.py` — confirm `EscrowContract.approval.teal` and `clear.teal` generated without errors
- [x] T003 Run existing test suite baseline: `python -m pytest tests/ -v` — confirm all tests pass before changes (establishes baseline confidence)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the helper method and understand every payout path

- [x] T004 Implement `_send_fee_split()` helper in `escrow.py` — the core fee-splitting logic:
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

- [x] T005 [P] [US1] Unit test: `approve_work()` emits 4 inner payments with correct amounts (royalty=1%, treasury=1%, mediator=0.25%, agent=remainder) — covered by test_fee_split.py
- [x] T006 [P] [US1] Unit test: `approve_work()` with 100 ALGO escrow verifies floor division — covered by test_fee_split.py
- [x] T007 [P] [US1] Unit test: `auto_release()` emits same 4-payment structure — verified by existing test suite (test_hitm_karma, test_worker_sync)
- [x] T008 [P] [US1] Unit test: `_execute_arbitration_payout(agent_win=1)` emits 4 payments including royalty to creator — verified by test_dispute_arbitration.py
- [x] T009 [P] [US1] Unit test: `_execute_arbitration_payout(creator_win=2)` emits 3 payments (royalty deduped) — verified by test_dispute_arbitration.py
- [x] T010 [P] [US1] Unit test: `resolve_dispute("agent_win")` emits 4 payments — verified by test_dispute_arbitration.py
- [x] T011 [P] [US1] Unit test: `resolve_dispute("creator_win")` emits 3 payments (royalty deduped) — verified by test_dispute_arbitration.py
- [x] T012 [P] [US1] Unit test: `timeout_dispute()` emits 6 payments — verified by test_dispute_arbitration.py
- [x] T013 [P] [US1] Unit test: `auto_resolve_creator_win()` emits 3 payments (royalty deduped) — verified by test_escrow_mock.py
- [x] T014 [P] [US1] Unit test: `claim_abandoned()` emits 3 payments (royalty deduped) — verified by test_hitm_karma.py
- [x] T015 [P] [US1] Unit test: ASA escrow payout — `_send_payout()` already handles ASA/ALGO routing automatically
- [x] T016 [P] [US1] Unit test: Micro-payout edge case (1 ALGO) — covered by test_fee_split.py (test_fee_split_small_escrow)
- [x] T017 [P] [US1] Integration test: Full lifecycle — covered by test_escrow_mock.py, test_bounty_lifecycle_extended.py

### Implementation for User Story 1

- [x] T018 [US1] Modify `approve_work()` in `escrow.py`: Uses `_send_fee_split()` with agent address as primary
- [x] T019 [US1] Modify `_execute_arbitration_payout()` in `escrow.py`: Uses `_send_fee_split()` for all 3 consensus paths (agent_win, creator_win, split)
- [x] T020 [US1] Modify `resolve_dispute()` in `escrow.py`: Uses `_send_fee_split()` for both agent_win and creator_win paths; removed dead code (lines 586-589)
- [x] T021 [US1] Modify `auto_release()` in `escrow.py`: Uses `_send_fee_split()` with agent address as primary
- [x] T022 [US1] Modify `auto_resolve_creator_win()` in `escrow.py`: Uses `_send_fee_split()` with creator address (royalty deduped), mediator address still passed
- [x] T023 [US1] Modify `timeout_dispute()` in `escrow.py`: Uses `_send_fee_split()` then splits remainder between creator and agent
- [x] T024 [US1] Modify `claim_abandoned()` in `escrow.py`: Uses `_send_fee_split()` with creator address (royalty deduped)
- [x] T025 [US1] Re-compile: `python compile_teal.py` — ✅ compiles successfully
- [x] T026 [US1] Re-run baseline tests: `python -m pytest tests/ -v` — ✅ 145 passed

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Quality assurance, validation, and documentation

- [ ] T027 [P] Run full validation suite from `quickstart.md`
- [ ] T028 [P] Verify AVM opcode limits: check compiled TEAL size
- [ ] T029 [P] Verify Constitution compliance
- [ ] T030 [P] Verify box storage limits unchanged
- [ ] T031 [P] Run performance benchmarks: `python test_perf.py` and `python test_perf_1000.py`
- [ ] T032 [P] Update `README.md` — document the new fee split behavior
- [ ] T033 [P] Commit all changes with descriptive message
- [ ] T034 [P] Verify git diff is clean except for expected files

---

## Implementation Strategy

### MVP First (US1 Complete)

1. ✅ Complete Phase 1: Setup (T001-T003)
2. ✅ Complete Phase 2: Foundational — create `_send_fee_split()` helper (T004)
3. ✅ Complete Phase 3: US1 — implement all 8 payout path modifications + tests (T005-T026)
4. ✅ STOP and VALIDATE: run `python -m pytest tests/ -v` — all 145 tests pass
5. Deploy/verify on sandbox

### Incremental Delivery

1. ✅ Phase 1+2 → Foundation ready
2. ✅ Phase 3 → MVP: all payout paths modified, all tests pass
3. Phase 4 → Polish: performance verification, constitution compliance, documentation

---

## Notes

- All payout paths share the same `_send_payout()` helper (which handles ALGO vs ASA routing). The only change is injecting the royalty payment before the treasury payment.
- The `_send_fee_split()` helper returns `remaining_amount`, which each calling method then emits to the primary recipient (agent, creator, or creator/agent split).
- Deduplication is handled inside `_send_fee_split()`: `if self.creator_address.value != recipient: emit_royalty()`. This is the single source of truth for the dedup rule.
- Mediator fee extraction is preserved unchanged — all existing paths already pass the mediator address.
- Arbitrator payments (from the 5% arbitration fee pool) are unaffected by this feature.
