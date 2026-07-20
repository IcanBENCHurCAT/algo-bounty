# Tasks: 003-byoa-github-integration

**Input**: Design documents from `/specs/003-byoa-github-integration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Verify project environment is on branch `003-byoa-github-integration`
- [ ] T002 Verify local Python and Algorand sandbox environments are active

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Update Database Models to include `authorized_app_id` and `hitm_enforced` in `gateway/database.py`
- [ ] T004 [P] Update `Escrow` smart contract state schema to include `authorized_app_id` in `escrow.algo`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Self-Hosted Gateway GitHub App Configuration (Priority: P1) 🎯 MVP

**Goal**: Configure GitHub App credentials in gateway configuration

**Independent Test**: Start gateway with valid GitHub App credentials and verify it connects without rate limit errors.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Update `gateway/config.py` to add `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`, and `GITHUB_INSTALLATION_ID`
- [ ] T006 [US1] Update GitHub authentication logic to use `jwt` generation in `gateway/github.py` instead of PATs

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Delegated Trust / HITM Enforcement (Priority: P1)

**Goal**: Smart contract and gateway logic to track authorized apps or enforce HITM

**Independent Test**: Unauthorized gateway fails to auto-approve, fallback correctly defaults to HITM mode.

### Implementation for User Story 2

- [ ] T007 [P] [US2] Implement tracking of `authorized_app_id` at bounty creation in `escrow.algo`
- [ ] T008 [P] [US2] Implement HITM mode fallback in `escrow.algo` when no authorized app is verified
- [ ] T009 [US2] Update webhook processing to validate incoming webhook payload signatures against configured GitHub App secrets in `gateway/github.py`
- [ ] T010 [US2] Update `gateway/routers/bounties.py` to pass the configured App ID during bounty creation transactions

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Secure Issue and Actor Binding (Priority: P2)

**Goal**: Securely tie the GitHub issue, repository, and actor to the claim for correct payout

**Independent Test**: PR closure correctly matches the GitHub actor to the registered wallet address.

### Implementation for User Story 3

- [ ] T011 [US3] Update issue closure webhook handler in `gateway/github.py` to securely extract issue, repo, and actor
- [ ] T012 [US3] Ensure the gateway verifies the actor's registered wallet address before triggering an approval transaction in `gateway/github.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T013 Code cleanup and refactoring in `gateway/github.py`
- [ ] T014 [P] Verify smart contract RekeyTo security guard and box limits (if contract changed)
- [ ] T015 Run quickstart.md validation to ensure BYOA setup works correctly end-to-end
- [ ] T016 [P] Update documentation for platform operators to detail GitHub App creation and configuration

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - integrates with US1's config
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - depends on webhook logic from US2
