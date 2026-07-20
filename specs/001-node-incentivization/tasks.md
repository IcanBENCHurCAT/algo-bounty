---
description: "Task list template for feature implementation"
---

# Tasks: Node Incentivization & Fee Splitting

**Input**: Design documents from `/specs/001-node-incentivization/`

**Prerequisites**: plan.md, spec.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify local environment is running and current test suite passes on `main` branch

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Update `Bounty` model in `gateway/supabase_migration.py` to include `gateway_address` column
- [x] T003 Update `BountyCreate` and `BountyResponse` schemas in `gateway/schemas.py` to include `gateway_address`
- [x] T004 Generate database migration via Alembic to apply `gateway_address` schema changes

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Specifying Gateway Node during Bounty Creation (Priority: P1) 🎯 MVP

**Goal**: As a bounty creator using a specific federated gateway, I want the gateway's address to be automatically registered with the smart contract, so that the infrastructure operator is incentivized.

**Independent Test**: Can be tested by creating a bounty and verifying the `gateway_address` is stored in the contract state.

## Implementation for User Story 1

- [x] T005 [P] [US1] Update `EscrowContract.__init__` in `escrow.py` to define `self.gateway_address = Box(Account, key="gateway_address")`
- [x] T006 [US1] Update `create_bounty` in `escrow.py` to accept `gateway_address: Account` and store it in `self.gateway_address.value`
- [x] T007 [P] [US1] Update `gateway/routers/bounties.py` to parse `gateway_address` and persist it to the database during bounty creation
- [x] T008 [US1] Update `tests/` files to pass `gateway_address` (or a zero address placeholder) to `create_bounty` in all relevant test transactions

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Gateway Node Receives Fee Split on Payout (Priority: P1)

**Goal**: As a federated gateway operator, I want to receive a portion of the platform fee when a bounty created through my node is successfully paid out, so that my infrastructure costs are covered.

**Independent Test**: Can be tested by completing a bounty and checking that the gateway address receives the correct fee amount in the atomic payout group.

## Implementation for User Story 2

- [x] T009 [US2] Update `_send_fee_split` in `escrow.py` to calculate fee split: 0.5% to `gateway_address` and 0.5% to `treasury_address` if gateway is set, otherwise full 1% to treasury.

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Transparent Fee Display (Priority: P2)

**Goal**: As a bounty creator or worker, I want to see the fee breakdown including the gateway node operator's cut, so that I understand where the platform fees are going.

**Independent Test**: Can be tested by viewing the bounty details page and observing the fee breakdown.

## Implementation for User Story 3

- [x] T010 [US3] Update frontend UI components in `dashboard/` to retrieve and render the Gateway Node Fee explicitly in all fee breakdown views

**Checkpoint**: All user stories should now be independently functional

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T011 [P] Run `compile_teal.py` to generate updated artifacts for `escrow.algo`
- [x] T012 [P] Verify smart contract box storage limits and RekeyTo security guards remain intact
- [x] T013 [P] Verify full test suite passes with `PYTHONPATH=. python -m pytest tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### Parallel Opportunities

- Foundation tasks can run in parallel
- Smart contract updates and API router updates in US1 can run in parallel
- UI update in US3 can run in parallel with US1/US2 backend changes once API schemas are updated in Foundational phase.
