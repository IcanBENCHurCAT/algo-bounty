# Data Model: GitHub App Integration & Trustless Payout Validation

## Key Entities

### WebhookDeliveryRecord (Idempotency Tracking)
Used to keep track of processed GitHub webhook delivery IDs (`X-GitHub-Delivery`) to prevent double-processing.

* **Fields:**
  - `id`: UUID (Primary Key)
  - `delivery_id`: String (Unique index, maps to `X-GitHub-Delivery`)
  - `processed_at`: DateTime (Default now)
  - `status`: String (processing, success, failed)

### Bounty (Modified/Referenced)
We map pull request links and check the `is_hitm` status.

* **Fields:**
  - `id`: Integer (Primary Key)
  - `app_id`: Integer (Algorand Application ID)
  - `is_hitm`: Boolean/Integer (0 for trustless)
  - `status`: String (open, claimed, submitted, closed)
  - `pr_url`: String (linked PR URL)
  - `worker_address`: String (Algorand wallet address of the claimer)
