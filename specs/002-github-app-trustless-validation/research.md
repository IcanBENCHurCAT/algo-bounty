# Research: GitHub App Integration & Trustless Payout Validation

## Summary of Findings

### 1. Webhook Signature Verification
* **Decision:** We use HMAC-SHA256 verification via FastAPI middleware or direct request parsing to validate the `X-Signature-256` header using the repository/app's webhook secret.
* **Rationale:** This prevents arbitrary external actors from hitting our webhook endpoint and claiming/releasing escrows.
* **Alternatives Considered:** None. Standard security requirement.

### 2. PR Merged Webhook Event Handling
* **Decision:** Inspect the `pull_request` payload to verify `action == "closed"` and `merged == true`. Check the PR title/body for `#ALGO-[0-9]+` and verify that the bounty's `is_hitm` is `0` (or `_k_hitm_enabled == 0`).
* **Rationale:** Keeps the workflow purely automated and trustless. If `is_hitm == 1`, we would run the review timeline instead.
* **On-chain Payout:** Trigger payout using `release_trustless` or equivalent method in `escrow.py` / `escrow.teal`.

### 3. Local Webhook Testing Strategy
* **Decision:** We mock the webhook payloads locally by sending POST requests to the `/webhooks/github` endpoint using `curl` or `pytest` with mock headers and signatures.
* **Rationale:** Avoids dependency on external tunnel providers like ngrok during core dev tests.
