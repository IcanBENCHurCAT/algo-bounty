# Quickstart Validation Guide: GitHub App Integration & Trustless Payout Validation

## Validation Scenarios

### 1. Mocking a PR Opened Webhook
To test that a Pull Request is linked to the bounty, we can mock the webhook payload.

```bash
# 1. Set environment variables
export WEBHOOK_SECRET="test-webhook-secret"

# 2. Run local API server (Port 8000)
python gateway/main.py

# 3. Trigger mock PR opened webhook
curl -X POST http://localhost:8000/webhooks/github \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: test-delivery-123" \
  -H "X-Signature-256: sha256=<generate-hmac-signature>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 105,
      "title": "Solve issue #ALGO-42",
      "body": "Fixes algorithm bug",
      "merged": false,
      "html_url": "https://github.com/org/repo/pull/105"
    }
  }'
```

### 2. Mocking a PR Merged Webhook
To test that the payout is trustlessly released upon merge:

```bash
curl -X POST http://localhost:8000/webhooks/github \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: test-delivery-124" \
  -H "X-Signature-256: sha256=<generate-hmac-signature>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "closed",
    "pull_request": {
      "number": 105,
      "title": "Solve issue #ALGO-42",
      "body": "Fixes algorithm bug",
      "merged": true,
      "html_url": "https://github.com/org/repo/pull/105"
    }
  }'
```
Check that the SQLite/Supabase database updates the bounty status to `CLOSED` and that the on-chain payout transaction succeeds.
