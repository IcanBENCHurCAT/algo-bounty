# Phase 1: Data Model

## Entities

### Bounty State (Fallback Representation)
- `bounty_id` (string): Extracted or mapped from on-chain state/app ID.
- `app_id` (number): The Algorand application ID.
- `status` (string): Derived from the contract state.
- `creator` (string): Algorand address of the creator.
- `worker` (string): Algorand address of the worker (if claimed).
- `amount` (number): Escrowed amount.
- `is_hitm` (boolean): Whether Human-in-the-Middle is enabled.

## State Transitions
In fallback mode, state transitions are **Disabled**. Mutating actions (Create, Claim, Approve, Dispute) are hidden or blocked in the UI to prevent desynchronization with the offline Gateway.
