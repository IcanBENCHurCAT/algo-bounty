# Tasks: Direct-to-Chain Fallback

**Input**: Design documents from `/specs/002-direct-to-chain-fallback/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Update `dashboard/package.json` to ensure `algosdk` utility availability (already installed).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [ ] T002 Implement a custom hook `useFallbackMode` in `dashboard/src/hooks/` to manage the fallback state (active/inactive) across components.
- [ ] T003 Implement `dashboard/src/services/indexerFallback.ts` to encapsulate the direct `algosdk` / AlgoNode public indexer API calls for fetching application box state.

---

## Phase 3: User Story 1 - Read-Only Fallback on API Failure (Priority: P1)

**Goal**: As a user, when the Gateway API is offline, fallback to querying a public Algorand indexer directly to view bounties in read-only mode.

**Independent Test**: Stopping the Gateway API still loads bounties via public indexers, and read-only mode indicators show up, disabling state-mutating actions.

### Implementation for User Story 1

- [ ] T004 [US1] Update `dashboard/src/components/BountyList.tsx` (or equivalent list component) to catch 5xx/Network errors when calling Gateway API and toggle `useFallbackMode`.
- [ ] T005 [P] [US1] When in fallback mode, route `BountyList` queries through the new `indexerFallback.ts` service instead.
- [ ] T006 [P] [US1] Update `dashboard/src/components/BountyDetail.tsx` (or equivalent detail component) to handle fallback mode and decode box state data correctly.
- [ ] T007 [US1] Implement a global UI banner or indicator in `dashboard/src/components/Layout.tsx` that prominently displays "Read-Only / Fallback Mode" when active.
- [ ] T008 [US1] Update all state-mutating UI elements (Create, Claim, Approve, Submit buttons) across the dashboard to be disabled or hidden when fallback mode is active, per the Data Model state transition constraints.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T009 Run `quickstart.md` Scenario 1 and Scenario 2 manual validations to ensure the fallback transition works cleanly and mutative actions are properly disabled.
- [ ] T010 [P] Verify `npm run typecheck` and `npm run build` pass in the `dashboard` directory.
