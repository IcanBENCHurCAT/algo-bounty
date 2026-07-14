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

- [ ] T001 Verify project workspace and compile tools are ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [ ] T002 Setup database schema for arbitrators and dispute_arbitrators in gateway/supabase_migration.py
- [ ] T003 Create Alembic migration for database updates in gateway/migrations/versions/add_arbitration.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Arbitrator Candidate Registration (Priority: P1) 🎯 MVP

**Goal**: Allow agents to register and deregister on-chain as candidate arbitrators.

**Independent Test**: Register high-karma agent, verify in box storage and DB.

### Tests for User Story 1
- [ ] T004 [P] [US1] Create unit tests for registration in tests/test_dispute_arbitration.py

### Implementation for User Story 1
- [ ] T005 [P] [US1] Implement register_arbitrator and deregister_arbitrator ABI methods in escrow.py
- [ ] T006 [P] [US1] Implement register and deregister REST endpoints in gateway/routers/arbitrators.py
- [ ] T007 [US1] Hook up arbitrators router in gateway/main.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Decentralized Arbitrator Selection and Voting (Priority: P2)

**Goal**: Automatically assign 3 random arbitrators when dispute is triggered, and record their votes.

**Independent Test**: Trigger dispute, assert selection of 3 random arbitrators, cast vote and verify.

### Tests for User Story 2
- [ ] T008 [P] [US2] Create integration tests for selection and voting in tests/test_dispute_arbitration.py

### Implementation for User Story 2
- [ ] T009 [US2] Update submit_dispute ABI method to select 3 random candidate arbitrators in escrow.py
- [ ] T010 [P] [US2] Implement vote_dispute ABI method in escrow.py
- [ ] T011 [P] [US2] Implement voting endpoint POST /api/v1/bounties/{bounty_id}/dispute/vote in gateway/routers/arbitrators.py
- [ ] T012 [US2] Update worker indexer to process arbitrator selection and vote logs in gateway/worker.py
- [ ] T013 [US2] Implement arbitrator replacement logic for inactive arbitrators on timeout in escrow.py and gateway/worker.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Dispute Resolution and Fee Payout (Priority: P3)

**Goal**: Execute payout to majority choice and distribute 0.05% fee to arbitrators.

**Independent Test**: Consensus reached, verify payout and fee split.

### Tests for User Story 3
- [ ] T014 [P] [US3] Create tests for payout and fee distribution in tests/test_dispute_arbitration.py

### Implementation for User Story 3
- [ ] T015 [US3] Implement resolution check and payout execution with 0.05% fee split in escrow.py and recompile the smart contract artifacts
- [ ] T016 [US3] Update worker indexer to parse resolution and payout events in gateway/worker.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T017 [P] Verify smart contract RekeyTo security guard and box limits in escrow.py
- [ ] T018 [P] Verify database operations work with both SQLite and Postgres engines in gateway/database.py
- [ ] T019 Verify integration by executing the quickstart.md validation scenario

---

## Dependencies & Execution Order

### Phase Dependencies
- Setup (Phase 1) is starting point.
- Foundational (Phase 2) blocks all stories.
- User Stories run sequentially in priority order (P1 → P2 → P3).

### Parallel Opportunities
- Test writing and implementation of registration endpoints can proceed in parallel.
- Voting endpoint and worker indexer task development can run in parallel.
