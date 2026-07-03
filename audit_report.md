# AlgoBounty Escrow Smart Contract - Hostile Audit Report

**Target:** `escrow.algo` (Algorand Python/Puya)
**Auditor:** Jules (Senior Security Researcher)
**Date:** 2024-05-24

## Executive Summary
The `escrow.algo` contract facilitates decentralized bounties on Algorand. While it incorporates several security features like rekey protection and basic group transaction checks, it contains several critical and high-severity flaws that could lead to theft of funds, permanent locking of escrows, or unauthorized state transitions.

---

## 1. Improper State Management (Critical)
### Severity: Critical
### Attack Path:
The contract uses `ptx.AppLocal.get/set` for the bounty state (`OPEN`, `CLAIMED`, etc.). In Algorand, Local State is stored in the account of the user who opted into the application.
1. The creator deploys the contract.
2. If the contract relies on Local State of the sender, different users will see different states for the same bounty.
3. An attacker can opt-in and have their own local `state` variable initialized, effectively bypassing the global state machine.
4. This allows multiple "agents" to claim the same bounty or bypass restrictions entirely because the contract is checking the *sender's* local state instead of a unified global state.

### Actionable Patch:
Migrate from `AppLocal` to `AppGlobal` or Global Boxes.
```python
def _state() -> UInt64:
    return ptx.AppGlobal.get_uint64(Bytes("state"))

def _set_state(val: UInt64) -> None:
    ptx.AppGlobal.set_uint64(Bytes("state"), val)
```

---

## 2. Missing Signature Verification in Dispute Resolution (Critical)
### Severity: Critical
### Attack Path:
The `resolve_dispute` method accepts a `mediator_signature` but never verifies it against a trusted public key.
1. A bounty enters the `DISPUTED` state.
2. An attacker (either creator or agent) calls `resolve_dispute` with a dummy `mediator_signature`.
3. The contract checks `resolution == "agent_win" | "creator_win"` and `mediator_signature.length() > 0`.
4. Since no cryptographic verification is performed, the attacker can force a payout or refund to themselves.

### Actionable Patch:
Store a trusted `mediator` address during `create_bounty` and use `op.ed25519verify`.
```python
# In resolve_dispute
mediator_addr = _box_get_address(Bytes("mediator"))
ptx.require(
    op.ed25519verify(resolution, mediator_signature, mediator_addr.address),
    "Invalid mediator signature"
)
```

---

## 3. Lack of On-Chain Payout Execution (High)
### Severity: High
### Attack Path:
The contract logs `payout_pending` but does not actually transfer funds. It assumes an off-chain processor will see the log and execute the payment.
1. This is a centralized point of failure. If the off-chain processor is compromised or goes offline, funds are stuck.
2. Users have no on-chain guarantee that "approving" work actually releases the money, as the contract doesn't use Inner Transactions to send the ALGO/ASA.

### Actionable Patch:
Use Inner Transactions (`itxn`) to automate payouts.
```python
def _send_payment(receiver: Account, amount: UInt64, asset_id: UInt64) -> None:
    if asset_id == Int(0):
        ptx.itxn.Payment(receiver=receiver, amount=amount).submit()
    else:
        ptx.itxn.AssetTransfer(
            xfer_asset=asset_id, asset_receiver=receiver, asset_amount=amount
        ).submit()
```

---

## 4. Incorrect Timestamp Units (Medium)
### Severity: Medium
### Attack Path:
The `escrow.teal` file (the compiled/fallback version) multiplies timeout constants by `1_000_000`.
1. `Global.latest_timestamp()` in Algorand returns seconds, not microseconds.
2. By multiplying by `1,000,000`, the 30-day timeout becomes 30,000,000 days.
3. This effectively breaks all timeout logic (`timeout_dispute`, `expire_claim`, `auto_release`), locking funds in the contract indefinitely if a party becomes unresponsive.

### Actionable Patch:
Remove the microsecond multiplier.
```python
DISPUTE_TIMEOUT = DISPUTE_TIMEOUT_DAYS * 24 * 60 * 60  # seconds
```

---

## 5. Unprotected Initialization (High)
### Severity: High
### Attack Path:
The `create_bounty` method can be called multiple times if not guarded.
1. An attacker can call `create_bounty` on an existing contract to reset the `creator_address`, `escrow_amount`, and `state`.
2. This allows them to hijack an existing escrow or reset the rejection count.

### Actionable Patch:
Add a check to ensure the contract hasn't been initialized.
```python
ptx.require(_box_get_uint64(Bytes("initialized")) == Int(0))
_box_put_uint64(Bytes("initialized"), Int(1))
```

---

## 6. Missing Receiver Verification in ASA Funding (High)
### Severity: High
### Attack Path:
In `_verify_escrow_funding`, the check for ASA transfers (`asset_id > 0`) validates the amount and asset ID but fails to verify that the contract itself is the receiver.
1. An attacker creates a bounty.
2. They include an Asset Transfer of the required amount to their *own* account in the same group.
3. The contract validates the transaction exists in the group and matches the amount/ID, but since it doesn't check the receiver, it marks the bounty as funded.
4. The bounty is created without the contract actually holding any assets.

### Actionable Patch:
Verify the `asset_receiver`.
```python
ptx.require(
    prev_tx.asset_receiver() == Global.current_application_address(),
    "Asset transfer must be to this app address"
)
```
