---
name: "algo-contract-practices"
description: "Guidelines and practices for writing Algorand smart contracts in Python (`algopy`) within this repository."
compatibility: "Python (`algopy`) smart contracts"
metadata:
  author: "algobounty-project"
  source: "custom-skills"
---

## Description
This skill covers essential Algorand Virtual Machine (AVM) limits and project conventions when writing smart contracts using `algopy` (Puya).

## Key Practices

### 1. Handling AVM Box Limits (The 8-Box Limit)
The AVM limits a single transaction to accessing a maximum of 8 boxes. To avoid exceeding this limit when contracts need to store multiple related pieces of data, you should pack multiple fields into a single `Box` using `arc4.Struct`.
```python
import algopy
from algopy import arc4

class WorkerData(arc4.Struct):
    address: arc4.Address
    bond_amount: arc4.UInt64
    did_hash: arc4.StaticArray[arc4.Byte, typing.Literal[32]]

# Use a single box to store the packed struct
worker_box = algopy.Box(WorkerData)
```

### 2. Static Array Typing
When defining an `arc4.StaticArray` inside a struct (or anywhere else in `algopy`), you **must** use `typing.Literal` for the array size for it to compile successfully with `algokit compile py`.
```python
import typing
from algopy import arc4

# Correct
my_array: arc4.StaticArray[arc4.Byte, typing.Literal[32]]

# Incorrect (will fail compilation)
# my_array: arc4.StaticArray[arc4.Byte, 32]
```

### 3. Safe Contract Deletion (Sweeping Funds)
In `algopy` smart contracts, methods with `allow_actions=["DeleteApplication"]` that sweep remaining ALGO to the creator must explicitly assert that the contract is in a safe state to prevent creators from prematurely closing active contracts and withdrawing funds.
```python
@arc4.abimethod(allow_actions=["DeleteApplication"])
def delete_application(self) -> None:
    # Ensure the contract is actually closed/completed before allowing deletion
    assert self.state_box.value == CLOSED, "Contract must be closed to delete"

    # Sweep remaining ALGO
    # ...
```

### 4. Fee Collection (Project Specific)
The `escrow.py` smart contract supports fee collection. When releasing payouts (via methods like `approve_work`, `timeout_dispute`, or `resolve_dispute`), the contract calculates and sends a 2% fee to a Treasury Account and a 0.25% fee to a Mediator Account. Be sure to account for these deductions and required accounts in the transaction group.

### 5. Deployment Two-Step Flow
Because an Algorand application ID is unknown during its `ApplicationCreateTxn`, bounty contract funding and state initialization occur in a separate transaction group *after* the contract is initially deployed by the backend (so the `app_id` is known).
