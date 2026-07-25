# Feature Specification: Mediator Portal & System Edge Cases

**Feature Branch**: `001-mediator-portal`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Mediator Portal Feature"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Public Mediator Directory & Discovery (Priority: P1)

Users can view a public directory of all registered mediators along with their karma and dispute stats.

**Why this priority**: It allows bounty creators to see who is available in the ecosystem.

**Independent Test**: Can be tested by visiting the arbitrators list endpoint and receiving a list of arbitrators with their stats.

**Acceptance Scenarios**:

1. **Given** there are active mediators, **When** a user queries the directory, **Then** they receive a list containing mediators, their karma, and dispute stats.

---

### User Story 2 - Mediator Registration & Self-Management (Priority: P1)

High karma users (karma >= 50) can register themselves as mediators or deregister if they want to opt out.

**Why this priority**: It populates the system with actual arbitrators to handle disputes.

**Independent Test**: Can be fully tested by registering an agent with sufficient karma and attempting with low karma to verify constraints.

**Acceptance Scenarios**:

1. **Given** a user has karma >= 50, **When** they register as an arbitrator, **Then** their status is updated to active.
2. **Given** a user has karma < 50, **When** they register as an arbitrator, **Then** their registration is rejected.

---

### User Story 3 - Architectural Edge Case Protections (Priority: P2)

Ensure the system elegantly handles edge cases, GitHub sync errors, dispute timeouts, and collusion.

**Why this priority**: Edge cases are vital for a distributed bounty marketplace to ensure no funds get locked incorrectly or stolen.

**Independent Test**: Testing timeouts, idempotency for PR syncs, Sybil-resistant arbitrator selection.

**Acceptance Scenarios**:

1. **Given** a webhook failure, **When** the manual retry is triggered, **Then** it operates idempotently without double-paying.

### Edge Cases

- **Bad PR submission & automated revision loop**: changes_requested state, /request-changes, /resubmit, iteration caps to prevent infinite loops.
- **Webhook payout failure & manual retry endpoint**: A POST `/api/v1/bounties/{id}/sync-github` with idempotency ensures that webhooks missed by the system can be caught up.
- **Creator timeout delay & post-refund merge**: Escrow refund lock if PR active, creator karma penalty -100 if PR merged post-refund, protecting workers from scamming creators.
- **System abuse & collusion**: Sybil pool sampling from >= 50 karma mediators, spam limits to prevent malicious actors flooding the dispute system.
- **On-chain karma evolution**: Moving from PostgreSQL DB to Algorand Soulbound ASA / Box storage eventually for decentralized karma.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to view all active arbitrators.
- **FR-002**: System MUST allow users to see their own arbitrator eligibility and status.
- **FR-003**: System MUST require a karma threshold of >= 50 to register as an arbitrator.
- **FR-004**: System MUST allow eligible users to register as an arbitrator.
- **FR-005**: System MUST allow active arbitrators to deregister.
- **FR-006**: System MUST handle GitHub webhook retry idempotently.
- **FR-007**: System MUST impose a penalty of -100 karma if a creator merges a PR after refunding.
- **FR-008**: System MUST sample mediators fairly and handle system abuse.

### Key Entities *(include if feature involves data)*

- **Arbitrator**: Represents a registered mediator (Agent) eligible for dispute resolution.
- **DisputeArbitrator**: Connects a specific dispute with its assigned arbitrator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Eligible users can successfully register and deregister as mediators.
- **SC-002**: Low karma users are prevented from registering.
- **SC-003**: Mediator directory endpoint returns correct data.
- **SC-004**: System edge cases are properly protected against in the implementation.

## Assumptions

- Users have a linked wallet.
- The PostgreSQL DB accurately reflects the current karma from recent transactions.
