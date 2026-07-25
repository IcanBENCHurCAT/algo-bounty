# Contract Specification: Admin API Endpoints

## Base Path
`/api/v1/admin`

## Security Dependency
All routes require header verification:
- `X-Admin-Address`: Must match `ADMIN_ADDRESS` in backend configuration.
- `Authorization`: Bearer JWT token issued to `ADMIN_ADDRESS`.

---

## Endpoints

### 1. `POST /api/v1/admin/disputes/{bounty_id}/resolve`
Executes an administrative resolution for a disputed bounty.

- **Request Body**:
  ```json
  {
    "resolution": "worker_win", // "worker_win" | "creator_win" | "split"
    "reason": "Code verified against GitHub PR specification"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "status": "closed",
    "bounty_id": "bounty-123",
    "resolution": "worker_win",
    "payout_type": "PAYOUT",
    "tx_id": "AB12CD34..."
  }
  ```

### 2. `GET /api/v1/admin/quarantines`
Lists all active and resolved account quarantines.

- **Response** (200 OK):
  ```json
  {
    "quarantines": [
      {
        "id": 1,
        "address": "ALGO_ADDRESS...",
        "bounty_id": "bounty-123",
        "reason": "post_refund_pr_merge",
        "details": "PR #45 merged after refund",
        "quarantined_at": "2026-07-25T12:00:00Z",
        "expires_at": "2026-07-28T12:00:00Z",
        "status": "active"
      }
    ],
    "total": 1
  }
  ```

### 3. `POST /api/v1/admin/quarantines/{quarantine_id}/resolve`
Resolves an active account quarantine.

- **Request Body**:
  ```json
  {
    "action": "clear", // "clear" | "penalize"
    "resolution_note": "User clarified pull request sync error",
    "karma_penalty": 0
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "status": "cleared",
    "quarantine_id": 1,
    "address": "ALGO_ADDRESS...",
    "action": "clear",
    "message": "Quarantine for ALGO_ADDRESS... updated to cleared."
  }
  ```
