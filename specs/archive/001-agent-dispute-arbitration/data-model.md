# Data Model: Decentralized Agent Dispute Arbitration

This document details the database schema additions and smart contract state/box storage layouts.

---

## 1. Database Model Changes

We add three main schemas/tables to the FastAPI database (represented in SQLAlchemy & Supabase Migration):

### `Arbitrator` (Table: `arbitrators`)
Represents registered candidate arbitrators.
- `address` (String, Primary Key): Algorand wallet address of the arbitrator agent.
- `status` (String, Default: "active"): Status of the arbitrator (`active`, `inactive`).
- `registered_at` (DateTime): Timestamp of candidate registration.

### `DisputeArbitrator` (Table: `dispute_arbitrators`)
Represents the many-to-many relationship of disputed bounties and assigned arbitrators.
- `id` (Integer, Primary Key, Autoincrement)
- `bounty_id` (String, ForeignKey to `bounties.bounty_id`, Index): The disputed bounty.
- `arbitrator_address` (String, ForeignKey to `arbitrators.address`, Index): Selected arbitrator address.
- `vote` (String, Nullable): Vote cast by this arbitrator (`worker`, `payer`, `split`, or `null`/pending).
- `voted_at` (DateTime, Nullable): Timestamp when the vote was submitted.

---

## 2. Smart Contract State (Boxes)

The smart contract uses global boxes to manage arbitrator registration and dispute assignment.

### Candidate Pool Storage
- **`candidate_count`** (`Box[UInt64]`): Central counter tracking the size of the active pool.
- **`candidate_at_[index]`** (`Box[Account]`): Maps sequential index to agent address.
- **`candidate_index_[address]`** (`Box[UInt64]`): Maps agent address to its sequential index for O(1) removal operations.

### Dispute Assignment Box
- **`dispute_arbitrators`** (`Box[DisputeData]`): Maps active dispute to its selected arbitrators and their vote records.
  - `DisputeData` ABI structure:
    ```python
    class DisputeData(arc4.Struct):
        arbitrator_1: arc4.Address
        arbitrator_2: arc4.Address
        arbitrator_3: arc4.Address
        vote_1: arc4.UInt64  # 0: Pending, 1: Worker, 2: Payer, 3: Split
        vote_2: arc4.UInt64
        vote_3: arc4.UInt64
        selection_timestamp: arc4.UInt64
    ```
