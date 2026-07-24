# Tasks: Platform Fee Splits Pre-Signed Validation in Web3 UX

**Input**: Design documents from `/specs/007-fee-split-ux/`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data Model**: [data-model.md](./data-model.md)
**Branch**: `007-fee-split-ux`

## Phase 1: Foundational — Fee Calculation Module

**Purpose**: Create the shared fee calculation logic that both backend and frontend will use.

- [ ] T001 [P] Create `gateway/schemas.py` fee model — add `FeeBreakdown` and `FeeBreakdownDisplay` Pydantic models (based on data-model.md), import in gateway schemas
- [ ] T002 [P] Create `dashboard/src/hooks/useFeeBreakdown.ts` — client-side fee calculation hook with same integer-division logic: `royalty = treasury = escrow * 2 // 100 // 2`, `mediator = escrow * 25 // 10000 if hitm else 0`, `claimant = escrow - royalty - treasury - mediator`

**Checkpoint**: Fee computation exists on both sides, verified with a small test script comparing Python and TypeScript results for the same escrow values.

## Phase 2: User Story 1 — Fee Split Display on Approve Payout (Priority: P2) 🎯 MVP

**Goal**: Creator sees fee breakdown in a modal before signing "Approve & Release"

**Independent Test**: Submit a bounty → open as creator → click "Approve & Release" → see fee breakdown → cancel closes modal without signing.

### Backend — API Extension

- [ ] T003 [US1] Modify `gateway/routers/bounties.py` `get_approve_txn` endpoint — after building the existing `ApplicationNoOpTxn`, read `escrow_amount` and `hitm_enabled` from bounty row (or boxes), compute `FeeBreakdown`, attach it to response as `fee_breakdown` field
- [ ] T004 [US1] Add `fee_breakdown.display` sub-object with ALGO-formatted strings to the response (FR-010: whole numbers for integer ALGO, 2 decimal places for < 1 ALGO)
- [ ] T005 [P] Add backend unit test `tests/test_fee_breakdown.py` — verify fee computation matches contract formula for edge cases: exact 1000 ALGO, small escrow (< 100 ALGO where 1% rounds to 0), non-HITM (mediator=0)

### Frontend — Approval Modal

- [ ] T006 [US1] Create `dashboard/src/components/ApproveModal.tsx` — modal component with: fee breakdown table (total, royalty, treasury, mediator, claimant), "Confirm & Sign" button, "Cancel" button. Use existing UI components (Button, Card) as pattern.
- [ ] T007 [US1] Create `dashboard/src/components/FeeBreakdownTable.tsx` — reusable component that renders the fee breakdown rows based on `hitm_enabled` flag (omits mediator line when false)
- [ ] T008 [US1] Modify `dashboard/src/app/bounties/[bounty_id]/page.tsx` — in `handleApprove()`, after calling `getApproveTxn`, check for `fee_breakdown` in response, open `ApproveModal` with the breakdown data and `unsigned_txn`, wire "Confirm & Sign" to proceed with wallet signature, wire "Cancel" to close modal without any API call
- [ ] T009 [P] Add WCAG 2.1 AA accessibility attributes to modal (ARIA labels, keyboard navigation, `role="dialog"`, focus trap)

**Checkpoint**: Approve flow shows fee breakdown modal. Cancel returns to bounty page without transaction. Confirm shows wallet signature with correct transaction group.

## Phase 3: User Story 2 — Fee Split Display on Dispute Resolution (Priority: P3)

**Goal**: Dispute resolution flows (auto-resolution, mediator resolution, arbitration) also show fee breakdown before signing.

**Independent Test**: Create a disputed bounty → resolve it → see fee breakdown in resolution modal.

- [ ] T010 [US2] Extend existing dispute modal in `dashboard/src/app/bounties/[bounty_id]/page.tsx` — when a resolution transaction is built (PAYOUT/REFUND/SPLIT), compute and display fee breakdown alongside existing resolution info
- [ ] T011 [US2] For REFUND type: show "No fees deducted — full refund" message instead of fee breakdown table
- [ ] T012 [US2] For SPLIT type (arbitration split): add arbitrator fee line (5% = `escrow * 50 // 10000`), show split percentages to each party
- [ ] T013 [P] Add backend support for dispute fee computation — if dispute resolution endpoints (`/{bounty_id}/resolve`, `/{bounty_id}/arbitrate`) currently return unsigned txn, extend response with `fee_breakdown` (same structure as approve, but with `payout_type` and optional `arbitrator` field)

**Checkpoint**: All dispute resolution flows display appropriate fee info.

## Phase 4: Testing & Validation

- [ ] T014 [P] Add frontend component test for `ApproveModal.tsx` — verify rendering of fee breakdown, verify cancel does nothing, verify confirm calls wallet signature
- [ ] T015 [P] Run quickstart.md validation scenarios (Scenario 1-4)
- [ ] T016 Verify SC-002: zero instances where displayed fee amounts differ from on-chain amounts (compare frontend display values against actual transaction group submitted)

## Phase N: Polish

- [ ] T017 Mobile viewport check (SC-004) — ensure fee breakdown modal renders on screen width ≤ 480px without horizontal scrolling
- [ ] T018 Add `tests/test_fee_breakdown_edge.py` — test integer division edge cases: escrow = 1 micro-ALGO, escrow = 1 ALGO, escrow = 0 (if possible), large escrow (10M ALGO)
- [ ] T019 Ensure git branch `007-fee-split-ux` is clean, commit, push

## Dependencies & Execution Order

1. **Phase 1** (T001, T002) → parallel, no inter-dependencies
2. **Phase 2** (T003–T009) → T003/T004 first (API), then T005 (tests), then T006/T007 (modal components), then T008 (integration), T009 (accessibility)
3. **Phase 3** (T010–T013) → after Phase 2, can run T011/T012/T013 in parallel once Phase 2 is done
4. **Phase 4** (T014–T016) → after all implementation
5. **Phase N** (T017–T019) → final polish

## Parallel Opportunities

- T001 and T002 are fully parallel (backend schema + frontend hook, same logic)
- T003 and T004 are parallel (API extension + response formatting)
- T006 and T007 are parallel (modal container + fee breakdown table component)
- T011, T012, T013 can run in parallel once Phase 2 is complete

## Phase 5: Convergence

**Purpose**: Close gaps identified by convergence assessment — accessibility, dispute resolution, test fixes, mobile polish.

- [x] T020 [F1] Add WCAG 2.1 AA attributes to approval/claim modals: role="dialog", aria-modal="true", aria-labelledby, aria-describedby, focus trap, Escape key close, focus return on close per FR-009 (HIGH)
- [x] T021 [F3] Fix 3 failing test assertions in test_fee_breakdown.py: test_exact_1000_algo (claimant=977.5 not 985), test_small_escrow_one_algo, test_small_escrow_rounding — verify against contract formula (HIGH)
- [x] T022 [F4] Extract inline fee breakdown table from page.tsx into dashboard/src/components/ui/FeeBreakdownTable.tsx per plan structure (LOW)
- [x] T023 [F5] Add frontend component test for FeeBreakdownTable: verify rendering, label, ARIA role=group (MEDIUM)
- [x] T024 [F6] Add mobile responsive styles to FeeBreakdownTable — verify at ≤480px viewport per SC-004, no horizontal scrolling (MEDIUM)
- [x] T025 [F7] Create tests/test_fee_breakdown_edge_cases.py with edge cases: escrow=1 microALGO, escrow=0, large escrow (10M ALGO), max 64-bit, odd amounts, mediator threshold (LOW)
- [x] T026 [F8] Extract inline modals from page.tsx into dashboard/src/components/ui/Modal.tsx + FeeBreakdownTable.tsx (LOW)
