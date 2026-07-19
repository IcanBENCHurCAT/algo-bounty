# Research: Decentralized Agent Dispute Arbitration

This document outlines the research, alternatives, and technical design decisions for implementing the decentralized dispute arbitration mechanism.

---

## 1. Candidate Pool Storage on Algorand

### Decision
Store arbitrator candidates as individual boxes keyed by a sequential index, tracked by a central count box.
- `candidate_count`: A `Box(UInt64)` holding the total number of registered candidates.
- `candidate_at_[index]`: A `Box(Account)` mapping an integer index `[0, count-1]` to the registered agent's address.
- `candidate_index_[address]`: A `Box(UInt64)` mapping an agent's address back to their index in the sequential list.

### Rationale
- **Gas Efficiency**: Storing all candidates in a single dynamic array or a single giant box is bound by size limitations (max 32KB per box) and requires rewriting the entire box upon updates, which incurs high gas costs.
- **O(1) Operations**: 
  - **Register**: Append to the end of the list (`candidate_at_[count] = address`, `candidate_index_[address] = count`, increment `count`).
  - **Deregister**: Swap the element to remove with the last element in the list, update indexes, and decrement `count`.
  - **Random Select**: Randomly generate an index $i \in [0, count-1]$ and fetch the candidate address in $O(1)$.

### Alternatives Considered
- *Off-chain registry in PostgreSQL*: Rejected. To be truly decentralized and trustless, candidate eligibility and assignment must be verifiable on-chain.
- *Single giant box with custom serialization*: Rejected due to complexity, maximum capacity restrictions, and expensive box write costs.

---

## 2. On-Chain Random Selection

### Decision
Generate pseudo-random indexes using the hash of transaction ID (`Txn.tx_id`) combined with block parameters.
- Seed: `op.sha256(Txn.tx_id.bytes + op.itob(Global.latest_timestamp))`
- Generate subsequent random numbers by hashing the previous value (`hash = op.sha256(hash)`).
- Select 3 distinct arbitrators who are not the bounty creator or the worker.

### Rationale
Avoids complex, costly oracle setups (like Chainlink VRF) while providing sufficient pseudo-randomness for selecting dispute resolvers directly inside the smart contract during the `submit_dispute` call.

---

## 3. Voting & Payout Resolution

### Decision
- Store the assigned arbitrators and their vote records as custom box storage for each active dispute.
- Votes:
  - `0`: No Vote (or Pending)
  - `1`: Worker (100% payout to worker)
  - `2`: Payer (100% refund to payer)
  - `3`: Split 50/50 (50% to worker, 50% to payer)
- Consensus is reached when the majority (e.g. 2 out of 3) vote for the same option.
- Resolution execution: On-chain payout of the bounty minus fees, including the 0.05% resolution fee split among voting arbitrators.

### Rationale
Simplifies state management while ensuring complete execution atomic logic where payout actions and state updates succeed or fail as a single atomic unit.
