# Feature Specification: Direct-to-Chain Fallback

**Feature Branch**: `[002-direct-to-chain-fallback]`

**Created**: 2026-07-19

**Status**: Draft

**Input**: User description: "We are building a sovereign frontend. The feature should update the Next.js frontend to optionally query public Algorand indexers directly if the Gateway API is offline, providing a read-only bypass so users can still view bounties."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read-Only Fallback on API Failure (Priority: P1)

As a user, when the Gateway API is offline or unreachable, I want the frontend to automatically fallback to querying a public Algorand indexer directly, so I can still view the status and details of bounties in a read-only mode.

**Why this priority**: Ensuring the application remains usable for viewing data even during backend outages is critical for a sovereign, decentralized application as mandated by Constitution Section 5.11.

**Independent Test**: Can be fully tested by stopping the local Gateway API server and refreshing the dashboard to verify that bounty listings still load via the public indexer.

**Acceptance Scenarios**:

1. **Given** the Gateway API is offline, **When** I navigate to the bounty list, **Then** the bounties should be fetched directly from a public Algorand indexer and displayed successfully.
2. **Given** the Gateway API is offline, **When** I view a specific bounty, **Then** the details should be loaded from the public indexer and interactions (like creating bounties) should be disabled or show appropriate warnings.

---

### Edge Cases

- What happens when both the Gateway API and the fallback public indexers are unreachable?
- How does system handle pagination or complex filtering when relying solely on public indexer endpoints vs the optimized Gateway API?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST attempt to fetch bounty data from the Gateway API first.
- **FR-002**: System MUST detect Gateway API unreachability (e.g., connection refused, 5xx errors) and automatically switch to a fallback mode.
- **FR-003**: System MUST query public Algorand indexers directly from the frontend when in fallback mode.
- **FR-004**: System MUST display a clear visual indicator to the user when operating in "Read-Only / Fallback Mode".
- **FR-005**: System MUST disable state-mutating actions (like creating or claiming a bounty) when relying exclusively on the fallback indexer, since the Gateway is required for indexing those actions correctly.

### Key Entities *(include if feature involves data)*

- **Bounty State**: Read-only representation of the bounty fetched directly from the Algorand blockchain via indexer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Frontend successfully loads and displays bounty data via public indexer within 3 seconds of detecting Gateway API failure.
- **SC-002**: 100% of state-mutating UI components are correctly disabled when in fallback mode to prevent inconsistent states.
- **SC-003**: Users receive a clear, human-readable notification that the app is in read-only mode.

## Assumptions

- Users have stable internet connectivity to reach public Algorand indexers.
- Public indexers rate limits are sufficient for the frontend's direct read-only query volume.
- The data schema returned by the public indexer can be mapped to the existing frontend state models.
