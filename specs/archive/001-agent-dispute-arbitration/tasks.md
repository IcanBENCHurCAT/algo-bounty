# Tasks: Decentralized Agent Dispute Arbitration

**Input**: Design documents from `/specs/001-agent-dispute-arbitration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify project workspace and compile tools are ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T002 Setup database schema for arbitrators and dispute_arbitrators in gateway/supabase_migration.py
- [x] T003 Create Alembic migration for database updates in gateway/migrations/versions/add_arbitration.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Arbitrator Candidate Registration (Priority: P1) 🎯 MVP

**Goal**: Allow agents to register and deregister on-chain as candidate arbitrators.

**Independent Test**: Register high-karma agent, verify in box storage and DB.

### Tests for User Story 1
- [x] T004 [P] [US1] Create unit tests for registration in tests/test_dispute_arbitration.py

### Implementation for User Story 1
- [x] T005 [P] [US1] Implement register_arbitrator and deregister_arbitrator ABI methods in escrow.py
- [x] T006 [P] [US1] Implement register and deregister REST endpoints in gateway/routers/arbitrators.py
- [x] T007 [US1] Hook up arbitrators router in gateway/main.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Decentralized Arbitrator Selection and Voting (Priority: P2)

**Goal**: Automatically assign 3 random arbitrators when dispute is triggered, and record their votes.

**Independent Test**: Trigger dispute, assert selection of 3 random arbitrators, cast vote and verify.

### Tests for User Story 2
- [x] T008 [P] [US2] Create integration tests for selection and voting in tests/test_dispute_arbitration.py

### Implementation for User Story 2
- [x] T009 [US2] Update submit_dispute ABI method to select 3 random candidate arbitrators in escrow.py
- [x] T010 [P] [US2] Implement vote_dispute ABI method in escrow.py
- [x] T011 [P] [US2] Implement voting endpoint POST /api/v1/bounties/{bounty_id}/dispute/vote in gateway/routers/arbitrators.py
- [x] T012 [US2] Update worker indexer to process arbitrator selection and vote logs in gateway/worker.py
- [x] T013 [US2] Implement arbitrator replacement logic for inactive arbitrators on timeout in escrow.py and gateway/worker.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Dispute Resolution and Fee Payout (Priority: P3)

**Goal**: Execute payout to majority choice and distribute 0.05% fee to arbitrators.

**Independent Test**: Consensus reached, verify payout and fee split.

### Tests for User Story 3
- [x] T014 [P] [US3] Create tests for payout and fee distribution in tests/test_dispute_arbitration.py

### Implementation for User Story 3
- [x] T015 [US3] Implement resolution check and payout execution with 0.05% fee split in escrow.py and recompile the smart contract artifacts
- [x] T016 [US3] Update worker indexer to parse resolution and payout events in gateway/worker.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T017 [P] Verify smart contract RekeyTo security guard and box limits in escrow.py
- [x] T018 [P] Verify database operations work with both SQLite and Postgres engines in gateway/database.py
- [x] T019 Verify integration by executing the quickstart.md validation scenario

---

## Dependencies & Execution Order

### Phase Dependencies
- Setup (Phase 1) is starting point.
- Foundational (Phase 2) blocks all stories.
- User Stories run sequentially in priority order (P1 → P2 → P3).

### Parallel Opportunities
- Test writing and implementation of registration endpoints can proceed in parallel.
- Voting endpoint and worker indexer task development can run in parallel.

---

## Phase 7: Convergence

- [x] T020 Add deregistration test (US1/AC3) to `tests/test_dispute_arbitration.py` — verify agent is removed from candidate pool on deregister call per FR-001 (missing)
- [x] T021 Add double-vote rejection test (US2/AC3) to `tests/test_dispute_arbitration.py` — assert contract rejects a second vote from the same arbitrator per FR-003 (missing)
- [x] T022 Add arbitrator selection integration test (US2/AC1) to `tests/test_dispute_arbitration.py` — trigger dispute, assert 3 arbitrators assigned, assert non-participants only per FR-002 (missing)
- [x] T023 Add payout and 0.05% fee distribution test (US3/AC1) to `tests/test_dispute_arbitration.py` — assert majority vote triggers correct fund split and per-arbitrator fee per FR-005/FR-006 (missing)
- [x] T024 Implement inactive arbitrator replacement logic in `gateway/worker.py` — detect arbitrators who miss vote deadline, replace from candidate pool, apply karma penalty per T013 / spec edge case (missing)
- [x] T025 Execute `specs/001-agent-dispute-arbitration/quickstart.md` validation scenario and record results per T019 (partial)
