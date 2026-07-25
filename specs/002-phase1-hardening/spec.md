# Feature Specification: Phase 1 Pre-Mainnet Hardening

**Feature Branch**: `002-phase1-hardening`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Phase 1 — Build NOW (Pre-Mainnet): Harden state machine (auto-transition to DISPUTED after MAX_REJECTIONS, disable refund from SUBMITTED), manual GitHub sync with idempotent pull-model payout, rename arbitrator to evaluator across platform, admin-only dispute resolution, replace auto-karma-penalty with quarantine state + 72hr admin review, document refund lock."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escrow State Machine Hardening (Priority: P1)

When a worker's submission is rejected the maximum number of allowed times, the system automatically escalates the bounty into a dispute state, preventing the contract from deadlocking in a terminal rejection state. Additionally, once a worker has submitted work, the bounty creator can no longer unilaterally reclaim the escrowed funds — the only paths forward are approval, further rejection (up to the cap), or formal dispute.

**Why this priority**: Without these guardrails, a creator can grief a worker by rejecting valid work until the cap is hit and then reclaiming funds. Conversely, a deadlocked contract means funds are permanently stuck. Both scenarios cause direct financial loss and destroy platform trust. This is the single most critical security gap identified by the five-persona architectural review.

**Independent Test**: Can be tested by simulating a full rejection cycle on a bounty and verifying that (a) the bounty automatically transitions to a dispute state after the final rejection, and (b) a refund request is denied while work is in a submitted state.

**Acceptance Scenarios**:

1. **Given** a bounty in "submitted" state with the maximum number of rejections already reached, **When** the creator issues a final rejection, **Then** the bounty automatically transitions to "disputed" state rather than remaining in a terminal "rejected" state.
2. **Given** a bounty in "submitted" state, **When** the creator attempts to reclaim the escrowed funds, **Then** the system rejects the refund request and informs the creator that a refund is not available while submitted work is pending review.
3. **Given** a bounty in "rejected" state (below the rejection cap), **When** the worker does not resubmit within a reasonable timeout period, **Then** the bounty reverts to "open" state, releasing the claim so another worker can attempt it.
4. **Given** a bounty in "claimed" state (no work submitted yet), **When** the creator requests a refund, **Then** the refund proceeds normally, as no work has been delivered.

---

### User Story 2 - Manual GitHub Synchronization (Priority: P1)

When an automated notification from GitHub fails to reach the platform (due to network outage, server downtime, or delivery failure), either the worker or any platform participant can manually trigger a synchronization check. The system verifies the current state of the linked code repository and updates the bounty status accordingly. Critically, the worker must personally authorize any fund release — the platform backend never unilaterally moves funds.

**Why this priority**: Automated notification failures are inevitable in production. Without a manual recovery path, completed work goes unpaid indefinitely, generating support tickets and destroying worker trust. The pull-model (worker authorizes payout) also reduces regulatory exposure by ensuring the platform never acts as an intermediary controlling fund flow.

**Independent Test**: Can be tested by completing a bounty's linked code contribution, disabling the automated notification path, and verifying that the manual sync button correctly detects the completed contribution and enables the worker to authorize their payout.

**Acceptance Scenarios**:

1. **Given** a bounty whose linked code contribution has been accepted but the automated notification was not received, **When** any user triggers a manual synchronization, **Then** the system detects the accepted contribution and updates the bounty status to reflect completion.
2. **Given** a bounty that has been manually synchronized and shows a completed contribution, **When** the worker authorizes the fund release, **Then** the escrowed funds are released to the worker with correct fee deductions.
3. **Given** a manual synchronization has already been processed for a bounty, **When** a second synchronization is triggered, **Then** the system recognizes it as a duplicate and does not create a second payout or alter the existing state.
4. **Given** a bounty whose linked code contribution has NOT been accepted, **When** a user triggers manual synchronization, **Then** the system reports that no state change is warranted and the bounty remains in its current state.

---

### User Story 3 - Platform Terminology Alignment ("Evaluator") (Priority: P1)

All user-facing references to "arbitrator" and "arbitration" across the platform are renamed to "evaluator" and "evaluation" (or equivalent neutral terminology such as "reviewer"). This ensures the platform's dispute resolution mechanism is clearly positioned as a community-driven technical quality assessment, not a legal arbitration proceeding.

**Why this priority**: Using the term "arbitration" in connection with binding financial outcomes creates legal liability under arbitration statutes (e.g., the Federal Arbitration Act in the US). Rebranding is a zero-cost, high-impact risk reduction identified unanimously by the architectural review panel.

**Independent Test**: Can be tested by searching the entire user-facing surface area (web interface, notification messages, documentation, and public-facing service endpoints) for the terms "arbitrator" or "arbitration" — zero matches should be found.

**Acceptance Scenarios**:

1. **Given** the platform's web interface, **When** a user navigates to any page, **Then** no user-visible text contains the words "arbitrator" or "arbitration."
2. **Given** the platform's public service endpoint paths, **When** a developer inspects the available endpoints, **Then** all dispute-related endpoints use "evaluator" or "reviewer" terminology.
3. **Given** the platform's notification messages and email templates, **When** a dispute-related notification is sent, **Then** the message uses "evaluator" or "evaluation" terminology.
4. **Given** the platform's data storage layer, **When** a developer inspects table or collection names, **Then** dispute-related entities use "evaluator" terminology.

---

### User Story 4 - Admin-Gated Dispute Resolution (Priority: P1)

During the platform's initial growth phase (Phase 1: Progressive Decentralization, per the project constitution Section 5.5), all dispute resolutions are handled by the platform administrator rather than an automated panel of community evaluators. The decentralized evaluator panel mechanism remains available but is only activated once the platform's trusted user base grows large enough to staff it reliably.

**Why this priority**: With a small early-stage user base, there are not enough high-reputation users to form impartial evaluation panels. Admin stewardship during Phase 1 ensures disputes are resolved fairly and quickly while building trust. Premature decentralization of dispute resolution creates a risk of deadlocked disputes with no qualified evaluators available.

**Independent Test**: Can be tested by triggering a dispute on a bounty and verifying that the resolution workflow routes to the platform administrator rather than selecting community evaluators.

**Acceptance Scenarios**:

1. **Given** the platform is operating in Phase 1 (admin stewardship mode), **When** a dispute is submitted on a bounty, **Then** the platform administrator is notified and can review the dispute evidence and render a resolution.
2. **Given** the platform administrator has reviewed a dispute, **When** the administrator selects a resolution (pay worker, refund creator, or split), **Then** the escrowed funds are distributed according to the administrator's decision.
3. **Given** the platform transitions to Phase 2 (community governance), **When** a dispute is submitted, **Then** the system selects community evaluators from the qualified pool instead of routing to the administrator.

---

### User Story 5 - Quarantine State for Suspicious Activity (Priority: P2)

When the system detects potentially abusive behavior (such as a creator reclaiming funds and subsequently accepting a worker's contribution off-platform), instead of automatically deducting reputation points, the system places the flagged account into a temporary quarantine state. During quarantine, the account's ability to create new bounties is suspended for 72 hours, and a platform administrator is notified to manually review the situation. The account holder is informed of the quarantine, the reason, and their right to appeal during the review window.

**Why this priority**: Automated reputation penalties without appeal violate due process principles, create false positive risks (e.g., an off-platform agreement between creator and worker), and may conflict with automated decision-making regulations in some jurisdictions. A quarantine-and-review model preserves platform safety while respecting user rights.

**Independent Test**: Can be tested by simulating the suspicious behavior pattern, verifying the account enters quarantine, confirming the admin is notified, and checking that the quarantine lifts after 72 hours or upon admin resolution.

**Acceptance Scenarios**:

1. **Given** suspicious activity is detected on an account (e.g., a post-refund contribution acceptance), **When** the system processes the detection, **Then** the account enters a "quarantined" state and cannot create new bounties.
2. **Given** an account is in quarantine, **When** the account holder views their profile, **Then** they see a clear notification explaining the quarantine reason, its duration (72 hours), and how to appeal.
3. **Given** an account has been in quarantine for 72 hours without admin action, **When** the quarantine period expires, **Then** the account is automatically restored to normal status.
4. **Given** a platform administrator reviews a quarantined account, **When** the administrator determines the activity was abusive, **Then** the administrator can apply a manual reputation penalty and extend restrictions.
5. **Given** a platform administrator reviews a quarantined account, **When** the administrator determines the activity was legitimate (e.g., an off-platform agreement), **Then** the administrator clears the quarantine immediately with no penalty.

---

### User Story 6 - Documented Refund Lock Policy (Priority: P2)

The platform's terms of service and user-facing documentation clearly state that once a worker has submitted work on a bounty, the escrowed funds are locked and cannot be unilaterally refunded by the creator. This policy is communicated to bounty creators at the point of bounty creation and reinforced in the bounty detail view whenever work has been submitted.

**Why this priority**: Clear communication of fund-locking rules prevents disputes arising from unmet expectations. Creators must understand before funding a bounty that once work is submitted, they are committed to the review process (approve, reject, or dispute) — they cannot simply withdraw.

**Independent Test**: Can be tested by verifying that refund lock language appears in the terms of service, the bounty creation flow, and the bounty detail view when work is in submitted status.

**Acceptance Scenarios**:

1. **Given** a user is creating a new bounty, **When** they reach the funding step, **Then** a prominent notice informs them that escrowed funds cannot be refunded once a worker submits work.
2. **Given** a bounty has work in "submitted" status, **When** the creator views the bounty detail page, **Then** a visible indicator confirms that the escrow is locked pending review.
3. **Given** the platform's terms of service, **When** a user reads the dispute and refund policy section, **Then** the refund lock rule is clearly documented with specific conditions under which refunds are and are not available.

---

### Edge Cases

- What happens if the platform administrator is unavailable during a Phase 1 dispute? The system should have a configurable escalation timeout (e.g., 14 days) after which the dispute auto-resolves in favor of the worker (analogous to existing HITM timeout behavior).
- What happens if the "evaluator" rename breaks existing integrations? External consumers of the platform's service endpoints should receive deprecation notices and a migration period with aliased endpoints.
- What happens if a quarantine is applied to a user with active bounties? Active bounties remain unaffected — only the ability to create *new* bounties is suspended during quarantine.
- What happens if the manual synchronization endpoint is abused (rate limiting)? Standard rate limiting should apply to prevent denial-of-service via repeated sync requests.
- What happens if the worker never authorizes payout after manual sync detects a merged contribution? After a configurable timeout period, the system should notify the worker and optionally allow the platform administrator to process the payout on the worker's behalf.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically transition a bounty to "disputed" state when the maximum rejection count is reached, rather than deadlocking in a terminal "rejected" state.
- **FR-002**: System MUST reject refund requests for bounties in "submitted" state — the creator cannot unilaterally reclaim escrowed funds once work has been delivered.
- **FR-003**: System MUST allow refund requests for bounties in "claimed" state (work not yet submitted) and "open" state.
- **FR-004**: System MUST provide a manual synchronization mechanism that checks the current state of the linked code repository and updates the bounty status when automated notifications fail.
- **FR-005**: System MUST require the worker to personally authorize fund release after a successful synchronization — the platform backend MUST NOT unilaterally trigger payouts (pull model).
- **FR-006**: Manual synchronization MUST be idempotent — repeated triggers for the same bounty MUST NOT create duplicate payouts or state changes.
- **FR-007**: All user-facing text, notification messages, documentation, and public service endpoint paths MUST use "evaluator" (or "reviewer") instead of "arbitrator" and "evaluation" instead of "arbitration."
- **FR-008**: Data storage entity names for dispute-related records MUST use "evaluator" terminology.
- **FR-009**: During Phase 1 (admin stewardship), dispute resolution MUST route to the platform administrator rather than selecting community evaluators.
- **FR-010**: The platform administrator MUST be able to render a dispute resolution (pay worker, refund creator, or split) through a dedicated administrative interface.
- **FR-011**: System MUST place accounts exhibiting suspicious activity patterns into a "quarantined" state that suspends new bounty creation for 72 hours.
- **FR-012**: Quarantined users MUST receive a clear notification explaining the reason, duration, and appeal process.
- **FR-013**: The platform administrator MUST be able to review quarantined accounts and either clear the quarantine or apply manual penalties.
- **FR-014**: Quarantine MUST automatically expire after 72 hours if no administrator action is taken.
- **FR-015**: The bounty creation flow MUST display a prominent notice about the escrow refund lock policy.
- **FR-016**: The bounty detail view MUST display a visible indicator when the escrow is locked due to submitted work.
- **FR-017**: The terms of service MUST document the refund lock rule and the conditions under which refunds are available.

### Key Entities

- **Bounty**: Extended with a "quarantined_creator" flag and stricter state transition rules for the rejection-to-dispute escalation path.
- **Account Quarantine Record**: Tracks quarantined accounts, the triggering event, quarantine start/end times, admin review status, and resolution outcome.
- **Evaluator** (renamed from Arbitrator): Community member qualified to participate in dispute evaluation panels (Phase 2+).
- **Sync Record**: Tracks manual synchronization attempts per bounty for idempotency enforcement, recording the external state observed and the resulting action taken.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero bounties are able to deadlock in a terminal "rejected" state — 100% of bounties reaching the rejection cap automatically escalate to dispute.
- **SC-002**: Zero refund requests succeed when a bounty has submitted work — refund lock is enforced without exception.
- **SC-003**: Workers can recover stuck payouts via manual synchronization within 2 minutes, without filing a support ticket.
- **SC-004**: Zero instances of the terms "arbitrator" or "arbitration" appear anywhere in the user-facing platform surface.
- **SC-005**: 100% of Phase 1 disputes are resolved by the platform administrator within 14 days of submission.
- **SC-006**: Zero users receive automated reputation penalties without a 72-hour review window and notification.
- **SC-007**: The refund lock policy is visible to 100% of users during bounty creation (confirmed by presence of the notice in the creation flow).

## Assumptions

- The existing smart contract state machine supports the addition of a new state transition rule (rejected → disputed after max rejections). If not, a contract upgrade or redeployment is required, following the constitution's upgrade path (Section 5.4).
- The code repository integration (currently GitHub) provides a reliable read API to verify contribution status during manual synchronization, even when push notifications fail.
- The platform has a designated administrator account with escalated privileges for Phase 1 dispute resolution (per the constitution Section 5.5, Phase 1: Progressive Decentralization).
- The "evaluator" rename is a comprehensive search-and-replace across user-facing surfaces, service endpoints, and data storage — internal variable names in non-public code may be renamed opportunistically but are not user-facing and thus lower priority.
- Account quarantine affects only the ability to create new bounties. Existing bounties, claim activities, and fund withdrawals are not affected by quarantine status.
- The terms of service are maintained as a platform document and can be updated without requiring smart contract changes.
