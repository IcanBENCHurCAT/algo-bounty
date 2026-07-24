# Feature Specification: GitHub App Integration & Trustless Payout Validation

**Feature Branch**: `002-github-app-trustless-validation`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Integrate and validate the GitHub App workflow in Trustless Mode (HITM = 0) to ensure correct webhook dispatching, PR linking, and automated escrow release on PR merge without manual reviews."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustless Bounty Setup & Creation (Priority: P1)

As Alice (the Creator), I want to deploy a trustless bounty (`is_hitm = 0`) from a GitHub issue so that contributors know that merging their PR will automatically release their payment.

**Why this priority**: Core step to initialize a trustless bounty and commit funds to the escrow contract.

**Independent Test**: Test by opening a GitHub issue with the bounty template using `is_hitm = 0`, verifying the smart contract is deployed on-chain with `is_hitm = 0` (or `_k_hitm_enabled = 0`), and confirming that the bot comments with the claim links.

**Acceptance Scenarios**:

1. **Given** a GitHub repository with the AlgoBounty App, **When** Alice creates a new issue labeled `bounty` with a reward amount and `is_hitm = 0`, **Then** the gateway MUST deploy the contract on-chain, lock the funds in trustless mode, label the issue `bounty:open`, and post a details comment.
2. **Given** a newly deployed trustless bounty, **When** the dashboard query fetches the bounty, **Then** it MUST display `is_hitm` as false / 0.

---

### User Story 2 - Automated PR Linking & Status Sync (Priority: P1)

As Bob (the Worker), I want my PR referencing `#ALGO-<ID>` to link to the bounty and show a status check on GitHub so that the link is confirmed.

**Why this priority**: Essential to connect the PR workspace to the on-chain escrow and provide feedback to the developer.

**Independent Test**: Test by opening a PR containing `#ALGO-<ID>`, checking that the gateway links the PR in the database and calls `link_proof(pr_url)` on-chain, and verifying that the bot labels the PR `bounty:reviewing`.

**Acceptance Scenarios**:

1. **Given** a claimed trustless bounty, **When** Bob opens a PR containing `#ALGO-<ID>` in the title or body, **Then** the gateway MUST automatically link the PR to the bounty record and register the proof URL in the escrow contract.
2. **Given** a linked PR, **When** the gateway processes the link event, **Then** the bot MUST post a PR comment confirming trustless mode is active and set the GitHub commit status check to `pending`.

---

### User Story 3 - Automated Escrow Release on PR Merge (Priority: P1)

As Bob (the Worker), I want the bounty escrow to pay out to me immediately when Alice merges my PR on GitHub so that the payment is released without manual intervention.

**Why this priority**: The key defining capability of the trustless workflow—merging code translates directly to secure payment.

**Independent Test**: Test by merging the linked PR on GitHub, verifying that the gateway processes the webhook, invokes the contract's trustless release logic on-chain, and transfers the funds.

**Acceptance Scenarios**:

1. **Given** a linked PR in `reviewing` state, **When** the maintainer merges the PR, **Then** the gateway MUST catch the `pull_request.merged` webhook, trigger the payout transaction (98% to worker, 2% to treasury) on-chain, and update the status to `CLOSED` in the database.
2. **Given** a successfully executed payout, **When** the transaction completes, **Then** the bot MUST label the issue and PR as `bounty:approved` and post a congratulatory comments with the payout transaction ID.

---

### Edge Cases

- **PR Closed Without Merge**: If Bob's PR is closed without being merged, the system MUST NOT release the escrow, and the bot MUST update the labels and status to allow other contributors to submit or claim.
- **Webhook Redelivery**: If GitHub triggers duplicate webhooks for the PR merge, the gateway's idempotency layer MUST ensure that the on-chain payout transaction is only executed once.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The gateway MUST expose an idempotent webhook receiver `/webhooks/github` that processes events for issues and pull requests, validating the payload against the webhook secret using HMAC-SHA256.
- **FR-002**: The gateway MUST detect references to `#ALGO-[0-9]+` inside incoming PR descriptions and titles, extracting the ID to link it to the corresponding database record.
- **FR-003**: In trustless mode (`is_hitm = 0`), the gateway MUST listen for the `pull_request.merged` event and automatically dispatch the transaction group to release on-chain funds.
- **FR-004**: The system MUST implement an idempotency check (e.g., using `X-GitHub-Delivery` in a Redis cache or SQLite sync table) to prevent duplicate transactions on multiple webhook dispatches.
- **FR-005**: The bot MUST automatically update the GitHub Issue and PR labels to sync state (`bounty:open`, `bounty:claimed`, `bounty:reviewing`, `bounty:approved`).

### Key Entities *(include if feature involves data)*

- **Bounty**: Holds configuration data including `app_id`, `amount`, `worker_address`, `is_hitm = 0`, and `status`.
- **SyncLog**: Tracks delivery status and transaction hashes of auto-releases to prevent dual executions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of webhook requests are signature-verified and acknowledged with a `200 OK` response under 500ms, running the database/contract changes asynchronously.
- **SC-002**: Trustless payout transaction group is submitted to the Algorand network within 3 seconds of the webhook processing the merged PR.
- **SC-003**: The bot updates labels and comments on the repository within 5 seconds of the transaction being confirmed.

## Assumptions

- **A-001**: The GitHub repository is configured with the webhook endpoint pointing to the FastAPI gateway's `/webhooks/github`.
- **A-002**: The webhook payloads contain the expected user login, PR status, and merge confirmation attributes standard to the GitHub platform.
