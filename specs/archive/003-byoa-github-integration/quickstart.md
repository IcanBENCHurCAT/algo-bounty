# Quickstart: Validation Guide

## Setup App Credentials
1. Create a GitHub App in your GitHub developer settings.
2. Generate a Private Key and note the App ID.
3. Install the app on your testing repository to get the Installation ID.
4. Set `.env` variables for the gateway:
   ```env
   GITHUB_APP_ID="your-app-id"
   GITHUB_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
   GITHUB_INSTALLATION_ID="your-installation-id"
   ```

## Test Scenario 1: Authorized Webhook
1. Start the gateway locally.
2. Create a bounty through the gateway.
3. Submit a webhook simulating a PR closure from the authorized repository.
4. Verify the gateway processes it and the smart contract accepts the auto-approval.

## Test Scenario 2: Unauthorized / HITM Fallback
1. Remove `GITHUB_APP_ID` from the gateway environment (or use a different ID).
2. Create a bounty.
3. Observe that the bounty creation enforces `hitm_enforced=True`.
4. Submit a webhook for closure.
5. Verify the gateway does not auto-approve, and instead requires the bounty creator to manually release funds.
