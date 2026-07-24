# Data Model: Node Incentivization & Fee Splitting

## 1. Smart Contract State Model (`EscrowContract`)

We introduce a new Box storage variable to track the optional federated gateway's node address.

### New Storage Box
- **Name**: `gateway_address`
- **Key**: `Bytes("gateway_address")`
- **Type**: `Account` (32 bytes)
- **Constraint**: Optional. If not registered, the box does not exist or holds the zero address.

---

## 2. Smart Contract ABI Update

The `create_bounty` ABI method signature is updated to:
- `create_bounty(byte[],uint64,uint64,uint64,uint64,address,address,address)void`

Parameters:
1. `bounty_id`: `byte[]`
2. `escrow_amount`: `uint64`
3. `is_hitm`: `uint64`
4. `asset_id`: `uint64`
5. `review_days`: `uint64`
6. `mediator`: `address`
7. `treasury`: `address`
8. `gateway_address`: `address` (optional/nullable equivalent, can pass zero address if none)

---

## 3. Database Schema Model (`bounties` Table)

We add a new column to the `bounties` database table to track which federated gateway facilitated the creation of the bounty.

### SQL / SQLAlchemy Changes
- **Table**: `bounties`
- **Column Name**: `gateway_address`
- **SQL Type**: `VARCHAR(58)`
- **SQLAlchemy mapping**: `gateway_address = Column(String(58), nullable=True)`
- **Default**: `None` (NULL)

---

## 4. API DTO / Schema Changes (`gateway/schemas.py`)

To allow clients (frontend/federated gateway) to provide the gateway address:

- **Schema**: `BountyCreate`
  - Add optional attribute: `gateway_address: Optional[str] = None`
- **Schema**: `BountyResponse` or database serialization
  - Expose `gateway_address` if set.
