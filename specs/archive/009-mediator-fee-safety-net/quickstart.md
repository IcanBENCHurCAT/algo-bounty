# Quickstart: Dynamic Mediator Fee Safety Net Validation Guide

This guide describes how to run and verify the dynamic mediator fee safety net and hosted indexer neutrality implementation.

---

## 1. Prerequisites

* Docker Compose running with LocalNet / AlgoKit localnet active.
* Python virtual environment active and dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```
* Gateway environment variables configured (`TESTING="True"` for test suite).

---

## 2. Validation Scenarios

### Scenario 1: HITM Payout Fee Redirection
* **Goal**: Verify that finishing a bounty in HITM mode redirects the 0.25% mediator fee to the worker's payout on-chain.
* **Execution**:
  1. Create a bounty with `is_hitm = 1`.
  2. Approve work submission.
  3. Verify that the claimant receives:
     $$\text{Payout} = \text{Escrow Amount} - \text{Platform Fees}$$
     (Confirm that the mediator fee is not deducted, meaning it's paid to the claimant).

### Scenario 2: Platform Fee Cap Enforced (API & On-Chain)
* **Goal**: Verify that setting a custom platform fee greater than 10% is rejected.
* **Execution**:
  1. Submit a POST request to `/api/v1/bounties/` with `platform_fee = 1200` (12%).
  2. Assert that the API responds with a `400 Bad Request` citing "Platform fee cannot exceed 10%".
  3. Deploy the smart contract via test script and call creation with a fee parameter set to `1200`. Assert that the contract execution fails on-chain.

### Scenario 3: Indexer Neutrality
* **Goal**: Verify that the backend crawler indexes bounties regardless of platform fee amount or treasury address overrides.
* **Execution**:
  1. Deploy an escrow contract with `platform_fee = 0` and `treasury_address` set to a dummy account.
  2. Trigger indexer parsing or wait for `gateway/worker.py` iteration.
  3. Query the `/api/v1/bounties` list endpoint and verify that the bounty is listed with the status and details intact.

### Scenario 4: Frontend Disclaimer Mandatory Check
* **Goal**: Verify that users cannot proceed without checking the disclaimers.
* **Execution**:
  1. Open the dashboard browser.
  2. Attempt to click "Connect Wallet" or "Create Bounty" with checkboxes unchecked.
  3. Assert that button remains disabled or prompts validation errors.
  4. Check the disclaimers and confirm the actions become active.
