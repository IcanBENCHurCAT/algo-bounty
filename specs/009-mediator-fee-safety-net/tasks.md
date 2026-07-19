# Tasks: Hosted Indexer Neutrality & Compliance Disclaimers

## Phase 1: Setup
- [x] T001 Configure local network defaults and test environment settings in `gateway/config.py`

## Phase 2: Foundational Database Updates
- [x] T002 Add `platform_fee` and `treasury_address` columns to `Bounty` model in `gateway/database.py` and `gateway/supabase_migration.py`
- [x] T003 Apply database migrations for `bounties` table updates

## Phase 3: Custom Treasury & Platform Fee Overrides
- [x] T004 Add unit test in `tests/` verifying database model column additions and migrations behavior
- [x] T005 Add validation for `platform_fee <= 1000` (10%) inside the smart contract `escrow.py`
- [x] T006 Update contract `_send_fee_split` in `escrow.py` to check dispute status/HITM mode and redirect the 0.25% mediator fee
- [x] T007 Add contract unit tests in `tests/` verifying the dynamic mediator fee redirection to worker on-chain
- [x] T008 Remove platform treasury filtering in `gateway/indexer.py` to ensure neutrality, replacing it with a basic schema check
- [x] T009 Update `gateway/indexer.py` to read `platform_fee` and `treasury_address` from global state and save them in the bounty database record
- [x] T010 Add indexer tests in `tests/` verifying that custom fee structure deployments are correctly indexed and persisted
- [x] T011 Update API schemas and routes in `gateway/routers/bounties.py` to accept `platform_fee` and `treasury_address` and validate `platform_fee <= 1000`
- [x] T012 Update backend fee estimation and payout split endpoints to return dynamically calculated splits
- [x] T013 Update `dashboard/src/hooks/useFeeBreakdown.ts` to redirect the mediator fee (0.25%) to the claimant's payout
- [x] T014 Update the "Advanced Settings" accordion in `dashboard/src/app/create/page.tsx` to expose inputs for custom platform fee and custom treasury address
- [x] T015 Run Playwright E2E tests simulating creation of a bounty with custom fee settings and checking the marketplace rendering

## Phase 4: P2P Tax & Agent Stewardship Disclaimers
- [x] T016 Add the mandatory peer-to-peer tax liability disclaimer checkbox in the bounty creation form (`dashboard/src/app/create/page.tsx`) and disable submission until checked
- [x] T017 Add the mandatory agent human steward disclaimer checkbox in the wallet connection modal/flow (`dashboard/src/components/WalletConnect.tsx`) and disable wallet connection/signing until checked
- [x] T018 Run Playwright E2E tests to verify that the connect-wallet flow and the bounty creation flow are blocked when checkboxes are unchecked

## Phase 5: Polish & Cross-Cutting Concerns
- [x] T019 Verify smart contract RekeyTo security guard and box storage limits are respected in `escrow.py`
- [x] T020 Verify database operations work correctly with both SQLite and Postgres engines in tests
- [x] T021 Run validation scenarios (Scenario 1, 2, 3, and 4)
- [x] T022 Update project documentation and markdown specs to reflect implemented state
