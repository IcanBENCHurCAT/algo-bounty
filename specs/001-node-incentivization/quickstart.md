# Quickstart / E2E Verification Guide: Node Incentivization

This guide describes how to verify the Node Incentivization & Fee Splitting functionality end-to-end.

## Prerequisites
1. Local Algorand Sandbox / LocalNet is running (`algokit localnet start`).
2. Gateway FastAPI service is running locally (`python gateway/main.py`).
3. Dashboard dev server is running (`npm run dev` in `dashboard/`).

## Verification Scenarios

### Scenario 1: Deploy & Create Bounty with Gateway Address
1. Submit a `POST /api/v1/bounties/` request with `gateway_address` specified:
   ```json
   {
     "bounty_id": "test-bounty-gateway-001",
     "amount": 10000000,
     "description": "Test bounty with gateway fee split",
     "repo_url": "https://github.com/test/repo",
     "gateway_address": "GATEWAY_WALLET_ADDRESS_HERE"
   }
   ```
2. Verify the API response returns `200 OK`.
3. Check the database `bounties` table to ensure `gateway_address` matches `"GATEWAY_WALLET_ADDRESS_HERE"`.
4. Inspect the application box state on the local sandbox for the key `gateway_address` to confirm it contains the correct public key bytes.

### Scenario 2: Payout with Fee Split
1. Trigger a successful payout on the created bounty.
2. Observe the transaction group on the blockchain (via sandbox logs or indexer).
3. Verify that the 2% fee is split as follows:
   - **Developer Royalty**: 1% to the creator.
   - **Platform Treasury**: 0.5% to the treasury address.
   - **Gateway Node**: 0.5% to the `gateway_address`.
4. Confirm the remaining 98% (minus mediator fees if applicable) goes to the worker.

### Scenario 3: Fallback Payout without Gateway Address
1. Create a bounty without specifying a `gateway_address`.
2. Trigger payout.
3. Verify that 1% goes to Developer Royalty and the full 1% goes to the Platform Treasury.
