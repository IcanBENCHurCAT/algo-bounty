# Tasks: GitHub App Integration & Trustless Payout Validation

**Input**: Design documents from `/specs/002-github-app-trustless-validation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are optional and included where appropriate for validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Includes exact file paths in descriptions.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Configure webhook secret and local testing env vars in `gateway/.env`
- [ ] T002 Verify sandbox localnet settings are configured in `gateway/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [ ] T003 Setup `WebhookDeliveryRecord` database model in `gateway/database.py`
- [ ] T004 Create database migrations for `WebhookDeliveryRecord` using alembic in `gateway/migrations/`

---

## Phase 3: User Story 1 - Trustless Bounty Setup & Creation (Priority: P1) 🎯 MVP

**Goal**: Support deploying on-chain escrows and posting confirmation comments when a bounty issue is created.

**Independent Test**: Run mock webhook curl script to trigger `issues.opened` and check issue label `bounty:open` and comment.

### Implementation for User Story 1

- [ ] T005 [US1] Create routing structure for `/webhooks/github` in `gateway/routers/github.py`
- [ ] T006 [US1] Implement issue parser logic for trustless mode (`is_hitm = 0`) in `gateway/routers/github.py`
- [ ] T007 [US1] Implement bot notification comment and `bounty:open` label logic in `gateway/github.py`

---

## Phase 4: User Story 2 - Automated PR Linking & Status Sync (Priority: P1)

**Goal**: Automatically link the PR to the bounty via references and set commit status check to pending.

**Independent Test**: Send mock PR opened webhook with `#ALGO-<ID>` reference and verify the PR is linked.

### Implementation for User Story 2

- [ ] T008 [US2] Implement PR opened webhook event handler in `gateway/routers/github.py`
- [ ] T009 [P] [US2] Implement `#ALGO-[0-9]+` regex reference detection helper in `gateway/github.py`
- [ ] T010 [US2] Implement PR opened comment and status check dispatcher in `gateway/github.py`

---

## Phase 5: User Story 3 - Automated Escrow Release on PR Merge (Priority: P1)

**Goal**: Release the on-chain escrow to the worker immediately upon PR merge webhook.

**Independent Test**: Send mock PR merged webhook and verify on-chain payout transaction executes successfully.

### Implementation for User Story 3

- [ ] T011 [US3] Implement PR merged event webhook handler in `gateway/routers/github.py`
- [ ] T012 [P] [US3] Implement idempotency check using `X-GitHub-Delivery` in `gateway/routers/github.py`
- [ ] T013 [US3] Implement on-chain `release_trustless` payout call in `gateway/algod_client.py`
- [ ] T014 [US3] Implement database status update to `CLOSED` on successful release in `gateway/routers/github.py`
- [ ] T015 [US3] Implement bot completion comment and `bounty:approved` label sync in `gateway/github.py`

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T016 Verify smart contract RekeyTo security guard and box limits during trustless operations
- [ ] T017 Run quickstart.md validation scenario tests locally using curl

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel or sequentially (US1 → US2 → US3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete
