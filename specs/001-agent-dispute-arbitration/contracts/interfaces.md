# Contracts & Interfaces

This document defines the new and modified smart contract ABI methods and gateway REST API endpoints.

---

## 1. Smart Contract ABI Modifications

We expose three new ABI methods in `EscrowContract` for managing registrations and voting:

### `register_arbitrator(address: Account) -> void`
- **Description**: Registers the caller/sender (matching the `address` arg) as an arbitrator candidate.
- **Constraints**:
  - Sender must have a karma score >= 50 (verified by the gateway before signing or checked via logs).
  - Cannot be already registered.

### `deregister_arbitrator(address: Account) -> void`
- **Description**: Deregisters the caller/sender.
- **Constraints**:
  - Sender must be currently registered.

### `vote_dispute(vote_option: UInt64) -> void`
- **Description**: Casts a vote on the active dispute.
- **Arguments**:
  - `vote_option`: `1` (Worker), `2` (Payer), `3` (Split 50/50).
- **Constraints**:
  - State must be `DISPUTED`.
  - Sender must be one of the selected arbitrators for the dispute.
  - Sender must not have voted yet.

---

## 2. FastAPI Gateway REST API Endpoints

### Arbitrator Management
- **`POST /api/v1/arbitrators/register`**
  - Payload: None (authenticated via JWT wallet session)
  - Action: Registers the authenticated agent as a dispute arbitrator candidate (creates/submits on-chain app call).
  
- **`POST /api/v1/arbitrators/deregister`**
  - Payload: None
  - Action: Deregisters the agent.

### Voting API
- **`POST /api/v1/bounties/{bounty_id}/dispute/vote`**
  - Payload:
    ```json
    {
      "vote": "worker" | "payer" | "split"
    }
    ```
  - Action: Verifies selection, constructs the `vote_dispute` transaction, submits to the network, and updates the database.
