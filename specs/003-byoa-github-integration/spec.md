# Feature Specification: BYOA GitHub Integration with Delegated Trust

**Feature Branch**: `003-byoa-github-integration`

**Created**: 2026-07-19

**Status**: Draft

**Input**: User description: "Spec 003: BYOA GitHub Integration with Delegated Trust. Context: We are moving to a Bring Your Own App (BYOA) model. The feature should update gateway/config.py and github.py to enforce GitHub App authentication. To prevent unauthorized auto-approvals, the smart contract must track which Gateway/App is authorized per-bounty, OR we must enforce HITM (Human-in-the-Middle) mode for all community-hosted nodes until on-chain OIDC is fully supported. Ensure we tie the correct close issue/repo/actor securely."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Self-Hosted Gateway GitHub App Configuration (Priority: P1)

As a platform operator running a community node, I need to configure my own GitHub App credentials so that I am not reliant on a centralized GitHub App for issue tracking and webhook processing.

**Why this priority**: Core to BYOA/BYOK principle to decentralize infrastructure and remove vendor lock-in.

**Independent Test**: Can be fully tested by starting the gateway with valid GitHub App credentials and verifying it connects to GitHub successfully without hitting centralized rate limits.

**Acceptance Scenarios**:

1. **Given** a new community-hosted gateway node, **When** the operator sets their GitHub App ID and private key in the environment variables, **Then** the gateway successfully authenticates and can manage webhooks for their configured repositories.
2. **Given** missing or invalid GitHub App credentials, **When** the gateway starts, **Then** it fails gracefully with clear errors indicating the required configuration.

---

### User Story 2 - Delegated Trust / HITM Enforcement (Priority: P1)

As a bounty creator, I need to know that only the specific gateway/app I authorized (or myself via HITM) can trigger auto-approvals for my bounty, so that unauthorized community nodes cannot fraudulently approve claims on my behalf.

**Why this priority**: Prevents malicious operators from automatically claiming or approving bounties they didn't create.

**Independent Test**: Can be fully tested by having an unauthorized gateway attempt to send an auto-approval payload and verifying it is rejected on-chain, while HITM mode correctly prevents automated payouts entirely.

**Acceptance Scenarios**:

1. **Given** a bounty created on a community-hosted node, **When** an unauthorized gateway attempts to submit an auto-approval, **Then** the smart contract rejects the transaction.
2. **Given** on-chain OIDC is not fully supported, **When** a bounty is created from a community-hosted node without an authorized app identity, **Then** the system automatically enforces HITM (Human-in-the-Middle) mode for that bounty.

---

### User Story 3 - Secure Issue and Actor Binding (Priority: P2)

As a worker claiming a bounty, I need the system to securely tie the GitHub issue, repository, and actor to the claim, so that I get credited correctly for my work.

**Why this priority**: Ensures fair and accurate payouts to the actual contributor.

**Independent Test**: Can be fully tested by submitting a valid PR to a bound repository and verifying the correct actor is credited upon issue closure.

**Acceptance Scenarios**:

1. **Given** a worker closes a linked GitHub issue, **When** the gateway processes the webhook, **Then** it accurately matches the GitHub actor to their registered wallet address before triggering an approval or notifying the creator.

### Edge Cases

- What happens when a gateway's GitHub App is uninstalled from a repository with active bounties?
- How does system handle webhooks that are delayed or received out of order?
- What happens if the GitHub App credentials expire or are rotated while bounties are active?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The gateway MUST support configuring GitHub App authentication (App ID, Private Key, Installation ID) in configuration securely.
- **FR-002**: The GitHub integration MUST use the configured GitHub App credentials to authenticate requests to the GitHub API, abandoning legacy personal access token patterns.
- **FR-003**: The system MUST uniquely identify and track which Gateway/App is authorized for each specific bounty at the time of creation.
- **FR-004**: The smart contract MUST enforce that auto-approvals are only accepted if signed by the specifically authorized Gateway/App, OR it MUST enforce HITM mode if no such trusted App is tracked.
- **FR-005**: The gateway MUST securely validate webhook payloads to ensure they originated from the configured GitHub App.
- **FR-006**: The system MUST securely bind the GitHub repository, issue ID, and actor to the bounty claim to prevent spoofing or misattribution.

### Key Entities

- **GitHub App Configuration**: Credentials and identifying information for a specific community node's GitHub App.
- **Bounty Escrow**: The on-chain state representing the bounty, updated to store the authorized Gateway/App identity or a flag enforcing HITM mode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of community-hosted nodes can configure and operate their own GitHub App without relying on the centralized AlgoBounty GitHub App.
- **SC-002**: 0 unauthorized auto-approvals can be successfully executed against bounties created on different nodes.
- **SC-003**: 100% of bounties lacking a verified authorized app identity default to HITM mode.
- **SC-004**: The gateway successfully processes GitHub webhooks and API calls using App authentication with 0 fallback to personal access tokens.

## Assumptions

- System operators have the necessary permissions to create and install a GitHub App for their repositories.
- The smart contract's state size limits can accommodate storing the authorized app identifier if needed.
- The existing OIDC bridge logic can be adapted or bypassed in favor of HITM mode until fully on-chain OIDC is implemented.
