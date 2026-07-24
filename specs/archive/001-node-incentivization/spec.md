# Feature Specification: Node Incentivization & Fee Splitting

**Feature Branch**: `[001-node-incentivization]`

**Created**: 2026-07-19

**Status**: Draft

**Input**: User description: "We are transitioning to a decentralized federated gateway network. The feature should modify the escrow.algo smart contract to accept a gateway_address upon bounty creation or payout, routing a portion of the 2% fee to that node. This creates a financial incentive for the community to run infrastructure."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Specifying Gateway Node during Bounty Creation (Priority: P1)

As a bounty creator using a specific federated gateway, I want the gateway's address to be automatically registered with the smart contract, so that the infrastructure operator is incentivized.

**Why this priority**: Essential for capturing the gateway address at the start of the bounty lifecycle.

**Independent Test**: Can be tested by creating a bounty and verifying the `gateway_address` is stored in the contract state.

**Acceptance Scenarios**:

1. **Given** a user is creating a new bounty on a federated frontend, **When** they submit the creation transaction, **Then** the frontend includes the gateway's node address in the transaction payload.
2. **Given** a bounty creation transaction, **When** it is processed by the smart contract, **Then** the `gateway_address` is persisted in the bounty's state box.

---

### User Story 2 - Gateway Node Receives Fee Split on Payout (Priority: P1)

As a federated gateway operator, I want to receive a portion of the platform fee when a bounty created through my node is successfully paid out, so that my infrastructure costs are covered.

**Why this priority**: Delivers the core financial incentive of the feature.

**Independent Test**: Can be tested by completing a bounty and checking that the gateway address receives the correct fee amount in the atomic payout group.

**Acceptance Scenarios**:

1. **Given** a completed bounty with a registered `gateway_address`, **When** the payout transaction is executed, **Then** 0.5% of the total payout is routed to the `gateway_address`.
2. **Given** a completed bounty without a registered `gateway_address`, **When** the payout transaction is executed, **Then** the standard full 1% platform treasury fee is routed to the central treasury.

---

### User Story 3 - Transparent Fee Display (Priority: P2)

As a bounty creator or worker, I want to see the fee breakdown including the gateway node operator's cut, so that I understand where the platform fees are going.

**Why this priority**: Ensures transparency and trust in the fee splitting mechanism, aligning with the constitution.

**Independent Test**: Can be tested by viewing the bounty details page and observing the fee breakdown.

**Acceptance Scenarios**:

1. **Given** a user is viewing a bounty with a `gateway_address`, **When** they look at the fee breakdown, **Then** they see a line item for the "Gateway Node Fee".

### Edge Cases

- What happens if the `gateway_address` cannot receive ALGO (e.g., minimum balance requirements not met)?
- What happens if the fee split calculation results in rounding errors or 0 ALGO (for very small bounties)?
- What happens if the `gateway_address` is identical to the creator or claimant address?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow the frontend/gateway to optionally provide a `gateway_address` when a new bounty is created.
- **FR-002**: Smart contract MUST store the `gateway_address` in the bounty's state.
- **FR-003**: System MUST route 0.5% of the total payout (half of the standard 1% Platform Treasury fee) to the `gateway_address` upon successful payout, if one is specified.
- **FR-004**: System MUST route the full 1% Platform Treasury fee to the central treasury if no `gateway_address` is specified.
- **FR-005**: Developer Royalty (1%) and Mediator fees (0.25%) MUST remain unaffected by this feature.
- **FR-006**: Frontend UI MUST display the gateway fee allocation transparently in all fee breakdowns.
- **FR-007**: Payout atomic transactions MUST include the payment to the gateway address if applicable.

### Key Entities

- **Bounty State**: Needs a new optional attribute for `gateway_address`.
- **Gateway Node**: Represents the infrastructure operator eligible for fee splits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Node operators successfully receive fee splits on 100% of successful payouts for bounties they facilitated.
- **SC-002**: Total fees extracted (developer + treasury + gateway + mediator) consistently sum to the expected 2.25% total.
- **SC-003**: Smart contract storage limits (box sizing) are not exceeded by the addition of the new address.
- **SC-004**: Frontend correctly renders the new fee split in the UI without visual degradation.

## Assumptions

- We assume a default fee split of 0.5% for the Gateway Node and 0.5% for the Platform Treasury (modifying the original 1% treasury allocation), while leaving the 1% Developer Royalty intact.
- We assume the frontend instance knows its own designated `gateway_address` via environment configuration and injects it into creation requests.
