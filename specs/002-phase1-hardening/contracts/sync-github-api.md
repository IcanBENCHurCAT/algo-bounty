# Contract: Manual GitHub Sync & Payout API

**Date**: 2026-07-25

## Endpoint: Sync GitHub State

```
POST /api/v1/bounties/{bounty_id}/sync-github
Authorization: Bearer <JWT> (any authenticated user)
Rate Limit: 10 requests per bounty per hour

Request Body: (none)

Response 200 (state changed):
{
  "status": "synced",
  "bounty_id": "ALGO-1234",
  "github_state": "merged",
  "previous_status": "submitted",
  "current_status": "submitted",
  "payout_ready": true,
  "message": "PR #42 has been merged. Worker can now claim payout."
}

Response 200 (no change):
{
  "status": "no_change",
  "bounty_id": "ALGO-1234",
  "github_state": "open",
  "payout_ready": false,
  "message": "GitHub state has not changed. PR is still open."
}

Response 200 (already processed):
{
  "status": "already_processed",
  "bounty_id": "ALGO-1234",
  "message": "This state change has already been processed."
}

Response 404:
{ "detail": "Bounty not found" }

Response 422:
{ "detail": "Bounty has no linked GitHub issue or PR" }

Response 429:
{ "detail": "Rate limit exceeded. Max 10 syncs per bounty per hour." }
```

### Sync Logic Flow

1. Fetch bounty from DB. Verify it exists and has a `github_issue_url` or `github_pr_url`.
2. Call GitHub API to get current issue/PR state.
3. Compute `idempotency_key = {bounty_id}:{merge_commit_sha}` (for PRs) or `{bounty_id}:{issue_closed_at_iso}` (for issues).
4. Check `sync_records` for existing record with this `idempotency_key`. If found, return `already_processed`.
5. If PR is merged or issue is closed:
   - Set `bounty.payout_ready = True`, `bounty.payout_ready_at = utcnow()`
   - Insert `sync_records` entry
   - Return `synced` with `payout_ready: true`
6. Otherwise, return `no_change`.

---

## Endpoint: Claim Payout (Worker Pull)

```
POST /api/v1/bounties/{bounty_id}/claim-payout
Authorization: Bearer <JWT> (worker only — must match bounty.worker address)

Request Body: (none)

Response 200:
{
  "status": "payout_complete",
  "bounty_id": "ALGO-1234",
  "tx_id": "TXID...",
  "amount": 1000,
  "message": "Payout of 1000 ALGO released to your wallet."
}

Response 403:
{ "detail": "Only the assigned worker can claim the payout." }

Response 409:
{ "detail": "Payout is not ready. Run sync-github first." }

Response 409:
{ "detail": "Bounty is already closed." }
```

### Claim Logic Flow

1. Verify JWT sender matches `bounty.worker` address.
2. Verify `bounty.payout_ready == True` and `bounty.status == "submitted"`.
3. Call `release_trustless(app_id, worker_address)` — same function used by webhooks.
4. On success: update `bounty.status = "closed"`, `bounty.payout_type = "PAYOUT"`, apply karma changes.
5. Return `payout_complete` with transaction ID.
