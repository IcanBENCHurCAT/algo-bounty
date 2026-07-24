# v12: Node Incentivization & Fee Splitting

This document details the architectural decisions made during the implementation of the Node Incentivization feature.

---

## Status
Approved / Implemented

## Context & Problem
We are transitioning to a decentralized federated gateway network. We need a way to incentivize community members to run infrastructure. We decided to split the platform treasury fee to route a portion of it to the gateway that facilitated the bounty.

## Decision
1. **Gateway Registration**: Gateway operators can register their address (`gateway_address`) during bounty creation.
2. **Fee Split**: The smart contract routes 0.5% of the total payout (half of the standard 1% Platform Treasury fee) to the registered `gateway_address` upon successful payout.
3. **Fallback**: If no `gateway_address` is provided, the full 1% platform fee goes to the central treasury.
4. **UI Transparency**: The frontend displays this "Gateway Node Fee" in all fee breakdown views.

## Consequences
**Positive**:
- Creates a financial incentive for the community to run infrastructure.
- Decentralizes the infrastructure footprint.
- Transparent fee sharing.

**Negative**:
- Adds a small amount of complexity to the smart contract payout logic.

## Superseded Decisions
- **0002-on-chain-fee-splits-and-mediator-net**: The 50/50 fee split logic is updated. While the Developer Royalty (1%) remains the same, the 1% Treasury fee is now further split dynamically if a gateway address is specified.
