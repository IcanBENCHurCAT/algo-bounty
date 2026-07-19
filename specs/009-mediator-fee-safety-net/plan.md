# Implementation Plan: Dynamic Mediator Fee Safety Net & Indexer Neutrality

**Branch**: `009-mediator-fee-safety-net` | **Date**: 2026-07-18 | **Spec**: [spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/009-mediator-fee-safety-net/spec.md)

---

## 1. Summary
This plan details the implementation of the Mediator Fee Safety Net (Constitution v2.1.0) and the Indexer Neutrality / Compliance features (Constitution v2.2.0).
* The 0.25% mediator fee allocation will be dynamically routed to the worker when no mediation takes place (HITM mode or undisputed Auto mode).
* The backend indexer will index all escrow contracts regardless of default fees.
* Creators can customize fees and treasury targets.
* Front-end disclaimers will outline peer-to-peer tax liability and agent stewardship rules.

---

## 2. Technical Context
* **Language/Version**: Python 3.12, TypeScript (Next.js 16)
* **Primary Dependencies**: `py-algorand-sdk`, `@algorandfoundation/algokit-utils`
* **Storage**: PostgreSQL (Supabase) / SQLite (Local dev) with new columns:
  * `platform_fee` (Integer representing basis points, defaults to `200`)
  * `treasury_address` (String representing Algorand address, defaults to the default platform treasury)
* **Testing**: `pytest`, Playwright E2E
* **Target Platform**: Algorand Sandbox / Testnet

---

## 3. Constitution Check
- [x] **Smart Contract Language**: Are all smart contracts written in Algorand Python and compiled via the Puya compiler? (AVM 12+)
- [x] **RekeyTo Protection**: Are all state-modifying contract methods protected by RekeyTo checks (`Txn.rekey_to() == Account(0)`)?
- [x] **Box Storage Limits**: Are keys and storage sizes inside boxes strictly limited?
- [x] **Karma Ledger Gatekeeping**: If the feature creates/claims, does it integrate with Karma?
- [x] **Escrow Funding Verification**: Does it implement dual-layer funding validation?
- [x] **Atomic Payout Group**: Are all payout/refund/splits atomic group transactions?
- [x] **OIDC Security**: Are GitHub automated tests validated securely?
- [x] **Database Compatibility**: Do DB operations support PostgreSQL and SQLite?
- [x] **Continuous Worker Setup**: Does the background worker/indexer run continuously in a non-throttled GCP environment?
- [x] **Mediator Fee Safety Net**: Payouts redirect the 0.25% mediator fee to the worker if HITM is enabled or if Auto mode is undisputed.
- [x] **Hosted Indexer Neutrality**: Verify that the indexer does not filter out or reject modified fee-split escrows.

---

## 4. Technical Design & Proposed Changes

### 4.1 Database Model Overrides
#### [MODIFY] `gateway/supabase_migration.py` and `gateway/database.py`
* Add columns to the `Bounty` model:
  * `platform_fee`: `Column(Integer, nullable=False, default=200)`
  * `treasury_address`: `Column(String(58), nullable=False, default="[DEFAULT_TREASURY_ADDRESS]")`
* Write corresponding SQL migration instructions for Supabase Postgres.

### 4.2 Smart Contract Changes (Fee Cap & Fee Redirection)
#### [MODIFY] `escrow.algo` / `escrow.py`
* Add validation in the contract instantiation/creation: verify `platform_fee <= 1000` (10%).
* Refactor `_send_fee_split` to check the dispute status (or accept it as an argument).
* If `is_hitm` is active or the bounty is settled without dispute, redirect the `fee_mediator` payout (0.25%) to the claimant's address.
* Ensure all payout branches are structured as atomic group transactions.

### 4.3 Neutral Indexer & Gateway API Changes
#### [MODIFY] `gateway/indexer.py`
* Remove filters that check if the deployment's treasury address matches the hardcoded platform address.
* Implement a basic schema check to verify that the deployed contract is indeed a valid instance of the `escrow.algo` application, but do not filter based on fees or treasury destinations.
* Retrieve the custom `platform_fee` and `treasury_address` from the application's global state and store them in the database bounty record.

#### [MODIFY] `gateway/routers/bounties.py`
* Add `platform_fee` and `treasury_address` parameters to the bounty creation schema/endpoint.
* Enforce `platform_fee <= 1000` in the endpoint validation.
* Update backend fee estimation endpoints to return the dynamically calculated splits reflecting the mediator fee redirection.

### 4.4 Frontend UI & Checkboxes
#### [MODIFY] `dashboard/src/hooks/useFeeBreakdown.ts`
* Update calculations so that the mediator fee (0.25%) is added to the claimant's payout when HITM is enabled or undisputed.

#### [MODIFY] `dashboard/src/app/create/page.tsx`
* Under an expandable "Advanced Settings" accordion, expose inputs for "Custom Platform Fee" (validated to be $\le 10\%$) and "Custom Treasury Address" (validated to be a valid Algorand address).
* Add a mandatory checkbox before submission: "I acknowledge that I am responsible for peer-to-peer tax reporting, compliance, and withholding obligations."

#### [MODIFY] `dashboard/src/components/WalletConnect.tsx`
* In the wallet connection modal/flow, add a mandatory checkbox: "I agree that any wallet controlled by an autonomous software agent must have a designated human steward who accepts full legal, tax, and financial responsibility."
* Disable the connect/signing buttons until this disclaimer is checked. State is stored purely in local/React component state.

---

## 5. Verification Plan

### Automated Tests
* **Contract/Symmetric Tests**: Add test cases to `tests/` verifying HITM and undisputed Auto mode fee splits, and testing the 10% fee cap enforcement.
* **Indexer Tests**: Add a test verification verifying that deployments with `platform_fee = 0` or custom treasury addresses are correctly indexed into the database.
* **Database Tests**: Verify migrations run and columns behave correctly.

### E2E / Playwright Tests
* Simulate user posting a bounty with custom fees, confirming advanced options work.
* Verify connect-wallet flow with disclaimers active.
