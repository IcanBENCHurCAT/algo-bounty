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

- [x] T001 Configure webhook secret and local testing env vars in `gateway/.env`
- [x] T002 Verify sandbox localnet settings are configured in `gateway/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T003 Setup `WebhookDeliveryRecord` database model in `gateway/database.py`
- [x] T004 Create database migrations for `WebhookDeliveryRecord` using alembic in `gateway/migrations/`

---

## Phase 3: User Story 1 - Trustless Bounty Setup & Creation (Priority: P1) 🎯 MVP

**Goal**: Support deploying on-chain escrows and posting confirmation comments when a bounty issue is created.

**Independent Test**: Run mock webhook curl script to trigger `issues.opened` and check issue label `bounty:open` and comment.

### Implementation for User Story 1

- [x] T005 [US1] Create routing structure for `/webhooks/github` in `gateway/routers/github.py`
- [x] T006 [US1] Implement issue parser logic for trustless mode (`is_hitm = 0`) in `gateway/routers/github.py`
- [x] T007 [US1] Implement bot notification comment and `bounty:open` label logic in `gateway/github.py`

---

## Phase 4: User Story 2 - Automated PR Linking & Status Sync (Priority: P1)

**Goal**: Automatically link the PR to the bounty via references and set commit status check to pending.

**Independent Test**: Send mock PR opened webhook with `#ALGO-<ID>` reference and verify the PR is linked.

### Implementation for User Story 2

- [x] T008 [US2] Implement PR opened webhook event handler in `gateway/routers/github.py`
- [x] T009 [P] [US2] Implement `#ALGO-[0-9]+` regex reference detection helper in `gateway/github.py`
- [x] T010 [US2] Implement PR opened comment and status check dispatcher in `gateway/github.py`

---

## Phase 5: User Story 3 - Automated Escrow Release on PR Merge (Priority: P1)

**Goal**: Release the on-chain escrow to the worker immediately upon PR merge webhook.

**Independent Test**: Send mock PR merged webhook and verify on-chain payout transaction executes successfully.

### Implementation for User Story 3

- [x] T011 [US3] Implement PR merged event webhook handler in `gateway/routers/github.py`
- [x] T012 [P] [US3] Implement idempotency check using `X-GitHub-Delivery` in `gateway/routers/github.py`
- [x] T013 [US3] Implement on-chain `release_trustless` payout call in `gateway/algod_client.py`
- [x] T014 [US3] Implement database status update to `CLOSED` on successful release in `gateway/routers/github.py`
- [x] T015 [US3] Implement bot completion comment and `bounty:approved` label sync in `gateway/github.py`

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T016 Verify smart contract RekeyTo security guard and box limits during trustless operations
- [x] T017 Run quickstart.md validation scenario tests locally using curl

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel or sequentially (US1 → US2 → US3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

---

## Phase 6: Convergence

- [x] T018 [US3] Add `WebhookDeliveryRecord` SQLAlchemy model to `gateway/database.py` and `gateway/supabase_migration.py` — required for idempotency per FR-004 / T003 (missing)
- [x] T019 [US3] Create Alembic migration for `WebhookDeliveryRecord` table in `gateway/migrations/versions/` per T004 (missing)
- [x] T020 [US3] Implement `X-GitHub-Delivery` idempotency check in `gateway/routers/webhooks.py` — persist delivery ID to `WebhookDeliveryRecord` before processing, return 200 immediately if already seen per FR-004 / T012 (missing)
- [x] T021 [US3] Add `release_trustless` payout function to `gateway/algod_client.py` — call escrow contract `approve_work` / payout ABI method with worker address and sign via platform key per T013 (missing)
- [x] T022 [US3] Invoke on-chain payout in `gateway/github.py` `handle_pr_event` on trustless PR merge — call `release_trustless` before updating DB status to `CLOSED` per FR-003 / US3/AC1 (partial)
- [x] T023 [US1] Add `bounty:open` label call in `gateway/github.py` `handle_issue_event` after bounty record is created per FR-005 / US1/AC1 (missing)
- [x] T024 [US2] Implement GitHub commit status check (`pending`) via `create_commit_status` API in `gateway/github.py` when PR is linked to a bounty per US2/AC2 (partial)
- [x] T025 [US3] Correct PR merge completion label from `bounty:completed` → `bounty:approved` in `gateway/github.py` per FR-005 / US3/AC2 (partial)
