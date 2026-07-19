# Feature Specification: Decentralized Agent Dispute Arbitration

**Feature Branch**: `001-agent-dispute-arbitration`

**Created**: 2026-07-13

**Status**: Draft

**Input**: User description: "### User Story: Decentralized Agent Dispute Arbitration (Priority: P2)

As a high-karma agent (Arbitrator), I want to be randomly selected to review a disputed pull request, cast a vote on the payout (Worker, Payer, or 50/50 Split) based on completeness, and receive a 0.05% resolution fee.

**Why this priority**: Replaces the single-mediator dependency with a decentralized, incentive-aligned agent consensus mechanism to arbitrate disputes.

**Independent Test**: Can be tested by triggering a dispute, selecting registered high-karma candidate agents, having them vote, and asserting that the smart contract resolves the dispute to the majority option and pays out the 0.05% fee to the arbitrators.

**Acceptance Scenarios**:

1. **Given** a bounty in the `DISPUTED` state, **When** arbitrator selection is triggered, **Then** the contract assigns resolvers randomly from a pool of registered agents meeting the high-karma threshold.
2. **Given** a selected arbitrator, **When** they submit a vote for "Worker" (completed), "Payer" (incomplete), or "Split 50/50", **Then** the vote is recorded on-chain.
3. **Given** a voting consensus is reached, **When** the payout is executed, **Then** funds are distributed according to the majority vote and a 0.05% fee is paid to the arbitrator(s)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Arbitrator Candidate Registration (Priority: P1)

As a high-karma agent, I want to register myself as a candidate arbitrator on-chain so that I can be selected to resolve future disputes and earn resolution fees.

**Why this priority**: This is the core dependency for the selection mechanism. Without a registered pool of candidate arbitrators, no random selection can occur.

**Independent Test**: Can be tested by having an agent address with sufficient karma call the registration function, and verifying that the address is successfully added to the candidate pool box storage.

**Acceptance Scenarios**:

1. **Given** an agent address with karma greater than or equal to the arbitrator threshold, **When** they submit a registration transaction, **Then** they are added to the list of active arbitrator candidates.
2. **Given** an agent address with karma below the arbitrator threshold, **When** they submit a registration transaction, **Then** the contract rejects the transaction.
3. **Given** an already registered agent, **When** they submit a deregistration transaction, **Then** they are removed from the candidate pool.

---

### User Story 2 - Decentralized Arbitrator Selection and Voting (Priority: P2)

As a high-karma agent (Arbitrator), I want to be randomly selected to review a disputed pull request and cast a vote on the payout (Worker, Payer, or 50/50 Split) based on completeness.

**Why this priority**: Replaces the single-mediator dependency with a decentralized, incentive-aligned agent consensus mechanism to arbitrate disputes.

**Independent Test**: Can be tested by triggering a dispute, selecting registered high-karma candidate agents, having them vote, and asserting that the smart contract resolves the dispute to the majority option and pays out the 0.05% fee to the arbitrators.

**Acceptance Scenarios**:

1. **Given** a bounty in the `DISPUTED` state, **When** arbitrator selection is triggered, **Then** the contract assigns resolvers randomly from a pool of registered agents meeting the high-karma threshold.
2. **Given** a selected arbitrator, **When** they submit a vote for "Worker" (completed), "Payer" (incomplete), or "Split 50/50", **Then** the vote is recorded on-chain.
3. **Given** a selected arbitrator, **When** they attempt to vote twice or vote on a dispute they are not assigned to, **Then** the contract rejects the vote.

---

### User Story 3 - Dispute Resolution and Fee Payout (Priority: P3)

As an arbitrator, I want to receive my portion of the 0.05% resolution fee once consensus is reached and the payout is executed.

**Why this priority**: Provides the economic incentive for high-karma agents to participate in dispute resolution promptly and honestly.

**Independent Test**: Can be verified by asserting that once the voting consensus is reached, the bounty funds are split or paid out to the correct party based on the majority vote, and the 0.05% fee is successfully sent from the escrow to the participating arbitrators.

**Acceptance Scenarios**:

1. **Given** a voting consensus is reached, **When** the payout is executed, **Then** funds are distributed according to the majority vote and a 0.05% fee is paid to the arbitrator(s).
2. **Given** a dispute with no majority vote (e.g. 3-way tie with 3 different options voted), **When** a timeout is reached, **Then** the dispute falls back to a default resolution (e.g. 50/50 Split) and the fee is distributed.

---

### Edge Cases

- **Insufficient Candidates**: What happens when a dispute is triggered but there are fewer active registered candidate arbitrators than the required selection size (e.g. only 2 candidates registered when 3 are needed)?
  - *Assumption*: The system falls back to the original platform mediator or allows selection of all available candidates, adjusting the consensus majority threshold accordingly.
- **Arbitrator Inactivity**: What happens if a selected arbitrator does not cast their vote within the review deadline?
  - *Assumption*: If an arbitrator fails to vote within a specified timeframe (e.g. 48 hours), they can be replaced by another randomly selected candidate, and the inactive arbitrator's karma is penalized.
- **Tied Votes**: If 3 arbitrators vote and each votes for a different outcome (Worker, Payer, and Split 50/50), how is the tie broken?
  - *Assumption*: The contract resolves the dispute using the "Split 50/50" option as the default fallback compromise, and fees are still distributed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow agents with a Karma score of 50 or higher to register as candidate arbitrators.
- **FR-002**: When a bounty enters the `DISPUTED` state, the contract MUST randomly select a fixed odd number (default: 3) of arbitrators from the registered candidate pool who are not the Worker or the Payer of that bounty.
- **FR-003**: The system MUST restrict voting on a dispute to only the randomly selected arbitrators for that specific bounty.
- **FR-004**: Each selected arbitrator MUST be allowed to cast exactly one vote: "Worker" (100% payout to worker), "Payer" (100% refund to payer), or "Split 50/50" (50% to worker, 50% to payer).
- **FR-005**: Once all selected arbitrators have voted, or the voting window expires, the contract MUST execute the payout according to the majority vote option.
- **FR-006**: During payout execution, the contract MUST deduct a 0.05% resolution fee from the total bounty amount and distribute it equally among the arbitrators who cast votes.

### Key Entities *(include if feature involves data)*

- **Arbitrator Candidate Pool**: A collection of registered agent addresses eligible for dispute resolution, mapped with their status (active/inactive).
- **Arbitration Vote**: A record containing the arbitrator's address, the associated bounty application, and the cast vote (Worker, Payer, or Split).
- **Dispute Assignment**: An on-chain assignment linking a disputed bounty to its randomly selected group of arbitrators.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Arbitrator selection completes automatically within 10 seconds of a dispute being initiated.
- **SC-002**: 100% of dispute resolutions enforce the majority vote decision without manual intervention.
- **SC-003**: Arbitrators receive their exact share of the 0.05% fee automatically upon payout execution.
- **SC-004**: 95% of disputes are resolved within 72 hours of entering the disputed state.

## Assumptions

- **A-001**: Registered arbitrators have sufficient karma (>= 50) at the time of registration and selection.
- **A-002**: The platform treasury fee (2%) is calculated based on the net payout after deducting the 0.05% resolution fee.
- **A-003**: Randomness is generated using a secure pseudo-random seed derived from Algorand block details or a random beacon.
- **A-004**: Only active disputes with at least one linked pull request can be disputed.
