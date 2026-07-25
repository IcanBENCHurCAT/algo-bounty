# Contract: Quarantine & Admin Dispute Resolution API

**Date**: 2026-07-25

## Admin Authentication

All admin endpoints require:
- `Authorization: Bearer <JWT>` where the JWT's wallet address matches the configured `ADMIN_ADDRESS` environment variable.
- Returns `403 Forbidden` if the caller is not the admin.

---

## Endpoint: Admin Resolve Dispute

```
POST /api/v1/admin/disputes/{bounty_id}/resolve
Authorization: Bearer <JWT> (admin only)

Request Body:
{
  "resolution": "worker_win" | "creator_win" | "split",
  "reason": "string (required, min 10 chars)"
}

Response 200:
{
  "status": "resolved",
  "bounty_id": "ALGO-1234",
  "resolution": "worker_win",
  "tx_id": "TXID...",
  "message": "Dispute resolved in favor of the worker."
}

Response 400:
{ "detail": "Invalid resolution. Must be worker_win, creator_win, or split." }

Response 404:
{ "detail": "Bounty not found or not in disputed state." }

Response 403:
{ "detail": "Admin access required." }
```

### Resolution Logic Flow

1. Verify caller is admin.
2. Verify bounty status == "disputed".
3. For "worker_win" or "creator_win": Call `resolve_dispute()` on the contract, signing with the platform's mediator key (same key used for `MediatorData.address`).
4. For "split": Call `timeout_dispute()` or implement a custom split via `resolve_dispute()` with mediator signature.
5. Update DB: `bounty.status = "closed"`, `bounty.payout_type = resolution`.
6. Apply karma adjustments per existing rules.
7. Log the admin action for audit trail.

---

## Endpoint: List Quarantined Accounts

```
GET /api/v1/admin/quarantines
Authorization: Bearer <JWT> (admin only)
Query Parameters:
  - status: "active" | "cleared" | "penalized" | "all" (default: "active")

Response 200:
{
  "quarantines": [
    {
      "id": 1,
      "address": "ALGO...",
      "reason": "post_refund_merge",
      "details": "Bounty ALGO-1234, PR #42 merged after refund",
      "quarantined_at": "2026-07-25T10:00:00Z",
      "expires_at": "2026-07-28T10:00:00Z",
      "status": "active",
      "resolved_by": null,
      "resolved_at": null
    }
  ],
  "total": 1
}
```

---

## Endpoint: Resolve Quarantine

```
POST /api/v1/admin/quarantines/{quarantine_id}/resolve
Authorization: Bearer <JWT> (admin only)

Request Body:
{
  "action": "clear" | "penalize",
  "karma_penalty": 0,          // Required if action == "penalize", 0-100
  "note": "string (required)"
}

Response 200:
{
  "status": "resolved",
  "quarantine_id": 1,
  "action": "clear",
  "message": "Quarantine cleared. Account restored to normal status."
}
```

### Resolve Logic Flow

1. Verify caller is admin.
2. Verify quarantine exists and `status == "active"`.
3. If "clear": Set `status = "cleared"`, `resolved_by = admin`, `resolved_at = utcnow()`.
4. If "penalize": Apply karma penalty (0-100), set `status = "penalized"`, record resolution.
5. Return updated quarantine record.

---

## Endpoint: User Quarantine Status (Public)

```
GET /api/v1/account/quarantine-status
Authorization: Bearer <JWT> (any authenticated user)

Response 200 (not quarantined):
{
  "is_quarantined": false
}

Response 200 (quarantined):
{
  "is_quarantined": true,
  "reason": "post_refund_merge",
  "quarantined_at": "2026-07-25T10:00:00Z",
  "expires_at": "2026-07-28T10:00:00Z",
  "appeal_instructions": "Your account has been temporarily restricted. An administrator will review your case within 72 hours. If you believe this is an error, please contact support."
}
```

---

## Quarantine Trigger Points

Quarantine is triggered by the background worker (`gateway/worker.py`) when it detects:

1. **Post-refund merge**: A bounty was refunded (via `claim_abandoned` or dispute resolution "creator_win"), but the worker's PR was subsequently merged on GitHub. Detected by comparing `bounty.payout_type == "REFUND"` and `bounty.github_pr_url` merge status.

2. **Repeated dispute losses**: A creator loses 3+ disputes within a 30-day window (tracked via `dispute_evaluators` history).

These detection rules are implemented in the worker's polling loop, not as real-time middleware.
