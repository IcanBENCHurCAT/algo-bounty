# AlgoBounty: TEAL Escrow Smart Contract Design (v4.0)

**State machine contract that powers every bounty — deposits, claims, releases, refunds, disputes, and GitHub verification. Implementation-ready reference synced with escrow.algo (Puya/pyTEAL source).**

---

## 1. Implementation Framework

| Property | Value |
|----------|-------|
| **Language** | Algorand Python (Puya compiler) — **NOT legacy PyTeal** |
| **AVM version** | 12 (current) |
| **Max program cost** | ~400,000 units |
| **Stack depth** | 1000 |
| **Max group size** | 16 transactions |
| **Deploy tool** | AlgoKit (algokit deploy) |
| **Test framework** | AlgoKit (algokit test) |

> **Critical:** Use the **Algorand Python Compiler (Puya)**. PyTeal is deprecated. The Puya compiler provides Python-native syntax that compiles directly to AVM bytecode, making state logic much easier to write and audit.

---

## 2. Revised State Machine: 8 States (v2)

Per security audit: **6 states → 8 states**, with new states for claim expiry and dispute timeout.

### Core States (app global `state` uint64)

| State | Value | Description |
|-------|-------|-------------|
| `OPEN` | 0 | Bounty visible, agents can claim |
| `CLAIMED` | 1 | Agent has claimed, working on it (48h clock starts) |
| `SUBMITTED` | 2 | Agent submitted work (proof URL + data) |
| `REJECTED` | 3 | Creator rejected — agent can revise and resubmit |
| `DISPUTED` | 4 | Either party contested → mediation window (30d clock starts) |
| `CLOSED` | 5 | Terminal state (payout or refund — determined by balance) |
| `DISPUTED_TIMEOUT` | 6 | *(Reserved)* Dispute auto-resolved with 50/50 split |
| `CLAIM_EXPIRED` | 7 | *(Intermediate)* Claim timeout fired, reverts to OPEN |

### Variables (stored in box storage, NOT separate states)

| Variable | Type | Description |
|----------|------|-------------|
| `payout_type` | bytes | `"PAYOUT"`, `"REFUND"`, or `"SPLIT"` — only relevant when `state == CLOSED` |
| `is_hitm` | uint64 | 1 if HITM mode (review window active), 0 for trustless |
| `review_deadline` | uint64 | Global.latest_timestamp when HITM review window expires |
| `rejection_count` | uint64 | Number of times work was rejected (anti-spam guard) |
| `escrow_amount` | uint64 | Amount locked in escrow (microALGO or ASA units) |
| `asset_id` | uint64 | ASA ID if bounty is in ASA (0 for ALGO native) |
| `creator_address` | address | Bounty creator's Algorand address |
| `agent_address` | address | Claiming agent's Algorand address |
| `proof_url` | bytes | GitHub PR link (<= 512 bytes) |
| `proof_data` | bytes | Structured proof data as JSON (<= 2048 bytes) |
| `created_timestamp` | uint64 | Global.latest_timestamp when created |
| `dispute_reason` | bytes | Dispute reason (<= 256 bytes) |
| `dispute_initiator` | address | Who initiated the dispute |
| **`claim_deadline`** | uint64 | **New:** Global.latest_timestamp when claim expires (48h after claim) |
| **`claim_timestamp`** | uint64 | **New:** Global.latest_timestamp when claim was set |
| **`github_status`** | bytes | **New:** "pending", "pass", or "fail" for GitHub verification |
| **`dispute_timestamp`** | uint64 | **New:** Global.latest_timestamp when dispute was filed |
| **`oidc_token`** | bytes | **New:** GitHub Actions OIDC token (off-chain validation) |

### State Diagram (v2)

```
┌──────────┐    claim_bounty()    ┌───────────┐    submit_work()    ┌───────────┐
│          │─────────────────────▶│           │────────────────────▶│           │
│   OPEN   │                      │  CLAIMED  │                     │ SUBMITTED │
│  (state=0)│◀─────────────────────│  (state=1)│◀─────────────────────│ (state=2) │
│          ││                   ▲  │           │                   │  │       │
│  reopened││           expire_  │  │           │                   │  │       │
│  (claim  ││            claim  │  │  approve_ │                   │  │       │
│  timeout)││            (48h)  │  │  work()   │                   │  │       │
│          ││              ▼    │  │           │                   │  │       │
└──────────┘│               CLAIM│           └──────┼───────────────┘  │
            ││                 │  │               │                   │
            ││         CLAIM_EXPIRED ──┐           │ reject_work()     │
            ││           (state=7)     │           ▼                   │
            ││                         │                       ┌───────────┐
            ││    submit_dispute()      │                       │           │
            │├──────────────────────────┘                       │ REJECTED │
            ││                                                  │  (state=3)│
            ││                       approve_work()            └────┼──────┘
            ││                               ▼                       │
┌──────────┐                     ┌──────────────────┐     revise_work() + submit_work()
│          │                     │                  │     ────────────────────────────┘
│  CLOSED  │◀────────────────────│     CLOSED       │
│  (state=5)│    payout_type=    │  (state=5)       │        (back to SUBMITTED)
│          │    PAYOUT/REFUND    │                  │
│          │    /SPLIT           └────────┬─────────┘
└──────────┘                             │
                                          │ submit_dispute()
                                          ▼
                                    ┌───────────┐
                                    │           │
                                    │  DISPUTED │  timeout_dispute() ──► CLOSED (SPLIT)
                                    │  (state=4)│  (30-day timeout,
                                    │           │   50/50 split)
                                    └─────┬─────┘
                                          │
                            ┌─────────────┼─────────────┐
                            │             │             │
                    resolve │        auto │     resolve
                   _dispute│      _resolve│     _dispute
                    (win)  │       _creat │    (with sig)
                           │      or_win  │
                           ▼              ▼
                    CLOSED ────────── CLOSED
                  (PAYOUT)         (REFUND)

HITM auto-release (from SUBMITTED, if is_hitm == 1 and review_deadline passed):
  └── auto_release() ──────────────────────────────► CLOSED (payout_type = "PAYOUT")

GitHub verification (from SUBMITTED, via off-chain processor):
  github_verify() ──────────────────────────────────► github_status = "pending"
  └── set_github_status("pass") ───────────────────► OFF-CHAIN: auto-approve
  └── set_github_status("fail") ───────────────────► OFF-CHAIN: auto-reject
```

### Transition Table (v2)

| Transition | Method | Who | To State | Notes |
|------------|--------|-----|----------|-------|
| OPEN → CLAIMED | `claim_bounty()` | agent | CLAIMED | Only one agent can claim; starts 48h claim timer |
| CLAIMED → SUBMITTED | `submit_work()` | agent | SUBMITTED | First submission |
| CLAIMED → CLAIM_EXPIRED → OPEN | `expire_claim()` | anyone | OPEN | 48h timeout; agent loses 20 karma |
| SUBMITTED → CLOSED | `approve_work()` | creator | CLOSED | payout_type = PAYOUT; client executes payment |
| SUBMITTED → REJECTED | `reject_work(reason)` | creator | REJECTED | Agent can revise (up to MAX_REJECTIONS) |
| SUBMITTED → DISPUTED | `submit_dispute(reason)` | either | DISPUTED | 30d timer starts |
| REJECTED → SUBMITTED | `submit_work()` (revise) | agent | SUBMITTED | Increments rejection_count |
| REJECTED → DISPUTED | `submit_dispute(reason)` | either | DISPUTED | 30d timer starts |
| REJECTED → CLOSED | `claim_abandoned()` | creator | CLOSED | After MAX_REJECTIONS; refund to creator |
| DISPUTED → CLOSED | `resolve_dispute(resolution, mediator_signature)` | either | CLOSED | resolution = "agent_win" or "creator_win" |
| DISPUTED → CLOSED | `timeout_dispute()` | anyone | CLOSED | 30-day timeout; 50/50 split (SPLIT) |
| DISPUTED → CLOSED | `auto_resolve_creator_win()` | anyone | CLOSED | Legacy 14-day from creation; creator wins (REFUND) |
| SUBMITTED → CLOSED | `auto_release()` | anyone | CLOSED | HITM timeout; payout_type = PAYOUT |
| SUBMITTED → SUBMITTED | `github_verify(pr_url, test_hash, oidc_token)` | agent | SUBMITTED | Stores OIDC data; status=pending |
| SUBMITTED → SUBMITTED | `set_github_status(status)` | off-chain processor | SUBMITTED | Updates status to pass/fail/pending |
| SUBMITTED → SUBMITTED | `get_bounty_info()` | anyone | SUBMITTED | Read-only; logs bounty metadata |
| CLOSED → (terminal) | — | — | — | No transitions allowed |

---

## 2a. Helper Functions

### 2a.1 Box Read/Write Helpers

The contract uses box storage for all mutable state. Helper functions abstract the bytes ↔ uint64/address conversions.

| Function | Read | Write |
|----------|------|-------|
| Bytes | `_box_get_bytes(key)` | `_box_put_bytes(key, value)` |
| uint64 | `_box_get_uint64(key)` | `_box_put_uint64(key, value)` |
| Address | `_box_get_address(key)` | `_box_put_address(key, value)` |

### 2a.2 State Management

| Function | Description |
|----------|-------------|
| `_state()` | Returns `ptx.AppLocal.get("state")` as uint64 |
| `_set_state(val)` | Sets app local `"state"` to val |

### 2a.3 Identity Checks

| Function | Description |
|----------|-------------|
| `_is_creator()` | Returns `True` if `Txn.sender() == box[creator_address]` |
| `_is_agent()` | Returns `True` if `Txn.sender() == box[agent_address]` and agent is non-zero |

### 2a.4 Security Guards

| Function | Description |
|----------|-------------|
| `_require_rekey_not_modified()` | Reverts if `Txn.rekey_to() != Account(32*0)` |
| `_verify_escrow_funding(amount, asset_id)` | Validates escrow payment in group tx |
| `_verify_escrow_balance(asset_id, amount)` | Validates contract holds required balance |

---

## 3. Escrow Funding Verification (SECURITY FIX)

### The Vulnerability (Before v2)

`create_bounty()` stored `escrow_amount` in box storage but **never verified that funds actually arrived**. A malicious actor could call `create_bounty()` with `escrow_amount=10_000_000` without sending any funds, creating a fake escrow that appears valid in the boxes but has zero balance.

### The Fix

`create_bounty()` now performs **two-layer verification**:

1. **Transaction Group Verification** (`_verify_escrow_funding()`):
   - Checks `Txn.group_index > 1` (must have a preceding transaction)
   - Gets the previous transaction via `ptx.Gtxn[Txn.group_index() - Int(1)]`
   - For ALGO: verifies `prev_tx.type_enum() == TypeEnum.Payment` AND `prev_tx.amount() == escrow_amount` AND `prev_tx.receiver() == Global.current_application_address()`
   - For ASA: verifies `prev_tx.type_enum() == TypeEnum.AssetTransfer` AND `prev_tx.xfer_asset() == asset_id` AND `prev_tx.asset_amount() == escrow_amount`

2. **Balance Verification** (`_verify_escrow_balance()`):
   - For ALGO: checks `Global.current_application_balance() >= escrow_amount`
   - For ASA: checks `AssetHolding.balance(app_address, asset_id).amount >= escrow_amount`

This dual verification ensures the escrow was both initiated correctly AND actually funded.

### Caller Requirements

When calling `create_bounty()`, the client must include the escrow payment in the transaction group:

```python
# AlgoKit example
group = [
    AppCallTxn(...),           # create_bounty call
    PaymentTxn(                # escrow payment
        receiver=app_address,
        amount=escrow_amount,
    ),
]
```

The contract validates that the payment in position `group_index - 1` matches exactly.

---

## 4. Payout Execution Model (SECURITY FIX)

### The Problem (Before v2)

Methods like `approve_work()`, `resolve_dispute()`, `auto_release()`, and `claim_abandoned()` all changed state to CLOSED and set `payout_type`, but **never actually transferred funds**. The funds were trapped in the contract's app account with no way to withdraw them.

### Why Smart Contracts Can't Send Funds Directly

In the Algorand AVM, a smart contract cannot initiate a payment by itself. To transfer funds FROM a contract, the contract must either:
1. Be **rekeyed** to a signing account (that account signs the payment)
2. Use an **atomic transfer group** where the client includes a PaymentTxn with the contract as the sender

### The Solution: Approval + Payment Pattern

Each payout method now:
1. **Verifies** the escrow balance is present
2. **Changes state** to CLOSED with the correct `payout_type`
3. **Logs** payout details for off-chain processing
4. The **client** executes the actual payment in the same atomic group

#### Required Group Transactions by Method

| Method | Payment Tx(s) | Recipient | Amount |
|--------|---------------|-----------|--------|
| `approve_work()` | 1 | agent_address | escrow_amount |
| `resolve_dispute(agent_win)` | 1 | agent_address | escrow_amount |
| `resolve_dispute(creator_win)` | 1 | creator_address | escrow_amount |
| `auto_resolve_creator_win()` | 1 | creator_address | escrow_amount |
| `timeout_dispute()` | 2 (split) | creator + agent | escrow_amount/2 each |
| `auto_release()` | 1 | agent_address | escrow_amount |
| `claim_abandoned()` | 1 | creator_address | escrow_amount |

#### AlgoKit Client Example

```python
from algokit import AlgoKit, AppClient

# Approve work and pay agent in atomic group
group = [
    AppCallTxn(
        app=app_client,
        on_complete=NoOp,
        method="approve_work",
    ),
    PaymentTxn(
        sender=app_client.app.address,  # contract as sender
        receiver=agent_address,
        amount=escrow_amount,
    ),
]
signer = TransactionSigner(multisig_address, signers)
app_client.sign_and_send(group, signer)
```

#### Method Signatures (Actual Implementation)

The contract does **NOT** accept `receiver`/`amount` as method parameters. The client executes payments as separate group transactions.

| Method | Parameters | State Guard | Purpose |
|--------|-----------|-------------|--------|
| `create_bounty(bounty_id, escrow_amount, is_hitm, asset_id)` | 4 | — | Deploy instance; escrow payment required in group |
| `claim_bounty()` | none | state=OPEN | Agent claims bounty; sets claim deadline |
| `submit_work(proof_url, proof_data)` | 2 | state=CLAIMED\|REJECTED | Submit/revise work |
| `approve_work()` | none | state=SUBMITTED, creator | Approves work; sets PAYOUT |
| `reject_work(reason)` | 1 | state=SUBMITTED, creator | Rejects work; increments counter |
| `submit_dispute(reason)` | 1 | state=SUBMITTED\|REJECTED, party | Starts dispute; records timestamp |
| `resolve_dispute(resolution, sig)` | 2 | state=DISPUTED, mediator sig | Resolves dispute |
| `auto_resolve_creator_win()` | none | state=DISPUTED, 14d old | Legacy: creator wins |
| `timeout_dispute()` | none | state=DISPUTED, 30d old | SPLIT 50/50 |
| `auto_release()` | none | state=SUBMITTED, HITM timeout | Auto-payout to agent |
| `claim_abandoned()` | none | state=REJECTED, max rejects | Refund to creator |
| `expire_claim()` | none | state=CLAIMED, 48h old | Revert to OPEN |
| `github_verify(pr_url, test_hash, oidc_token)` | 3 | state=SUBMITTED | Store OIDC data |
| `set_github_status(status)` | 1 | — | Update verification status |
| `get_bounty_info()` | none | — | Read-only metadata log |

#### Payment Group Transaction Requirements

For each payout method, the client must include the payment(s) in the same atomic group:

| Method | Payment Tx(s) | Recipient(s) | Amount(s) |
|--------|---------------|--------------|----------|
| `approve_work()` | 1 | agent_address | escrow_amount |
| `resolve_dispute("agent_win")` | 1 | agent_address | escrow_amount |
| `resolve_dispute("creator_win")` | 1 | creator_address | escrow_amount |
| `auto_resolve_creator_win()` | 1 | creator_address | escrow_amount |
| `timeout_dispute()` | 2 (split) | creator + agent | escrow_amount/2 each |
| `auto_release()` | 1 | agent_address | escrow_amount |
| `claim_abandoned()` | 1 | creator_address | escrow_amount |

## 5. New Security Features (v2)

### 5.1 Dispute Timeout (30 days)

**Method:** `timeout_dispute()`
**Who:** Anyone (permissionless)
**Transition:** DISPUTED → CLOSED
**Payout:** 50/50 split to creator and agent

When a dispute is filed (via `submit_dispute()`), a `dispute_timestamp` is recorded. If 30 days pass without resolution:

```python
DISPUTE_TIMEOUT_DAYS = Int(30)
DISPUTE_TIMEOUT = DISPUTE_TIMEOUT_DAYS * 24 * 60 * 60 * 1_000_000  # 30 days
_K_DISPUTE_TIMESTAMP = Bytes("dispute_timestamp")

def timeout_dispute(self) -> None:
    ptx.require(_state() == DISPUTED)
    dispute_ts = _box_get_uint64(_K_DISPUTE_TIMESTAMP)
    ptx.require(Global.latest_timestamp() > dispute_ts + DISPUTE_TIMEOUT)
    
    escrow_amount = _box_get_uint64(_K_ESCROW_AMOUNT)
    half_amount = escrow_amount / Int(2)
    
    _box_put_bytes(_K_PAYOUT_TYPE, SPLIT)
    _set_state(CLOSED)
    
    # Log: split to both parties (client executes 2 payments)
    Log(Bytes("dispute_timeout_split"))
```

**Why 50/50?** It incentivizes the mediator/creator/agent to resolve disputes promptly while protecting all parties from indefinite locks. If one party was clearly at fault, they can always resolve it manually before the timeout.

### 5.2 Claim Timeout (48 hours)

**Method:** `expire_claim()`
**Who:** Anyone (permissionless)
**Transition:** CLAIMED → CLAIM_EXPIRED → OPEN
**Penalty:** Agent loses 20 karma (logged for off-chain tracker)

If an agent claims a bounty but never submits work:

```python
CLAIM_TIMEOUT_HOURS = Int(48)
CLAIM_TIMEOUT = CLAIM_TIMEOUT_HOURS * 60 * 60 * 1_000_000  # 48 hours
_K_CLAIM_DEADLINE = Bytes("claim_deadline")
_K_CLAIM_TIMESTAMP = Bytes("claim_timestamp")

def claim_bounty(self) -> None:
    _box_put_uint64(_K_CLAIM_DEADLINE, Global.latest_timestamp() + CLAIM_TIMEOUT)
    _box_put_uint64(_K_CLAIM_TIMESTAMP, Global.latest_timestamp())

def expire_claim(self) -> None:
    ptx.require(_state() == CLAIMED)
    claim_deadline = _box_get_uint64(_K_CLAIM_DEADLINE)
    ptx.require(Global.latest_timestamp() > claim_deadline)
    
    _set_state(CLAIM_EXPIRED)
    Log(Bytes("claim_expired"))
    Log(Bytes("karma_penalty_20"))
    
    _set_state(OPEN)  # Reopen for others
    Log(Bytes("bounty_reopened"))
```

### 5.3 GitHub OIDC Bridge

**Method:** `github_verify()` + `set_github_status()`
**Who:** Agent (verify), off-chain processor (status)
**Purpose:** Automated verification of test results via GitHub Actions OIDC tokens

```python
_K_GITHUB_STATUS = Bytes("github_status")

def github_verify(self, pr_url: Bytes, test_hash: Bytes, oidc_token: Bytes) -> None:
    """Store GitHub verification data for off-chain processing."""
    ptx.require(_state() == SUBMITTED)
    _box_put_bytes(_K_PROOF_URL, pr_url)
    _box_put_bytes(_K_GITHUB_STATUS, Bytes("pending"))
    _box_put_bytes(_K_PROOF_DATA, test_hash)
    _box_put_bytes(Bytes("oidc_token"), oidc_token)

def set_github_status(self, status: Bytes) -> None:
    """Off-chain processor updates status: pass/fail/pending."""
    ptx.require(status == "pass" | status == "fail" | status == "pending")
    _box_put_bytes(_K_GITHUB_STATUS, status)
```

The off-chain processor:
1. Receives the OIDC token from `github_verify()`
2. Validates the JWT with GitHub's JWKS
3. Fetches the PR and test results
4. Updates status via `set_github_status("pass")` or `set_github_status("fail")`

Off-chain integration then triggers `approve_work()` or `reject_work()` based on status.

### 5.4 Read-Only Method

**Method:** `get_bounty_info()`
**Who:** Anyone (read-only)
**Purpose:** Return bounty metadata via log output for off-chain indexing

```python
def get_bounty_info(self) -> None:
    """Read-only view: return bounty metadata."""
    ptx.require(Txn.type_enum() == op.TypeEnum.AppCall)
    ptx.require(Txn.on_completion() == op.OnCompletion.NoOp)

    Log(Bytes("bounty_info"))
    Log(_state())                              # state value (uint64)
    Log(_box_get_bytes(_K_BOUNTY_ID))         # bounty_id (bytes)
    Log(_box_get_uint64(_K_ESCROW_AMOUNT).to_bytes())  # escrow_amount
    Log(_box_get_address(_K_CREATOR_ADDRESS).address)  # creator
    Log(_box_get_address(_K_AGENT_ADDRESS).address)    # agent (may be zero)
    Log(_box_get_uint64(_K_REJECTION_COUNT).to_bytes())  # rejection count
```

Off-chain indexers consume these logs to build dashboards without reading all boxes individually.

---

## 6. Security Design (Updated)

### 6.1 RekeyTo Protection

```python
def _require_rekey_not_modified() -> None:
    ptx.require(Txn.rekey_to() == Account(32 * b"\x00"))
```

Prevents compromised accounts from transferring the app. Applied to all write methods.

### 6.2 Escrow Funding Verification

```python
def _verify_escrow_funding(escrow_amount: UInt64, asset_id: UInt64) -> None:
    """Verify the payment in the transaction group matches escrow_amount."""
    ptx.require(Txn.group_index() > Int(1))
    prev_tx = ptx.Gtxn[Txn.group_index() - Int(1)]
    # ... type checks and amount checks
```

Prevents fake escrow creation (CRITICAL FIX).

### 6.3 Balance Verification Before Payout

```python
def _verify_escrow_balance(asset_id: UInt64, escrow_amount: UInt64) -> None:
    """Verify the contract actually holds the escrowed funds."""
    ptx.require(Global.current_application_balance() >= escrow_amount)
```

Applied to all methods that change state to CLOSED with a payout/refund/split.

### 6.4 Timeout Enforcement

- **Claim timeout:** 48 hours — prevents agents from hoarding bounties
- **Dispute timeout:** 30 days — prevents mediator ghosting
- Both use `Global.latest_timestamp()` (block timestamp, not manipulable)

### 6.5 Box Space Limits

- Proof data: <= 2048 bytes
- URLs: <= 512 bytes
- Dispute reason: <= 256 bytes
- Rejection count: uint64 (effectively unlimited)
- OIDC token: bounded by box storage limit (~4KB)

Prevents DoS via massive box storage.

### 6.6 Fee Model

- Flat 0.001 ALGO per App Call
- Maximum 3 App Calls per operation (payout requires 2 additional payments)
- Escrow funding: 2 App Calls (create_bounty + payment) = 0.002 ALGO
- Complete cycle: ~0.004-0.006 ALGO total

---

## 7. Indexer Warning (Critical)

> **Beware of Indexer Lag:** When integrating with the Algorand Indexer for the off-chain dashboard, indexers can lag behind consensus state by 1-2 blocks.

**Best Practice:**
- **Read-only actions** (dashboard view, search) -> Use the Indexer API
- **Critical state verification** (verifying bounty is claimable, ready for payout) -> Query the Algorand node (`algod`) directly via `ApplicationInfo`

The Indexer is fine for display purposes, but for transaction submission decisions, always verify state against the node.

---

## 8. Gas/Cost Analysis

| Operation | App Calls | Payments | Fees (ALGO) |
|-----------|-----------|----------|-------------|
| Create bounty | 1 | 1 (escrow) | 0.002 |
| Claim bounty | 1 | 0 | 0.001 |
| Submit work | 1 | 0 | 0.001 |
| Approve work | 1 | 1 | 0.002 |
| Reject work | 1 | 0 | 0.001 |
| Dispute work | 1 | 0 | 0.001 |
| Resolve dispute | 1 | 1 | 0.002 |
| Timeout dispute | 1 | 2 | 0.003 |
| Auto release | 1 | 1 | 0.002 |
| Claim abandoned | 1 | 1 | 0.002 |
| Expire claim | 1 | 0 | 0.001 |
| GitHub verify | 1 | 0 | 0.001 |
| GitHub status update | 1 | 0 | 0.001 |
| Get bounty info | 1 | 0 | 0.001 |
| **Total (happy path)** | **4** | **3** | **0.005** |
| **Total (disputed + resolved)** | **6** | **5** | **0.007** |

---

## 9. Unit Test Plan (AlgoKit)

See separate file: `tests/test_escrow_contract.py`

Key test cases:
1. `test_create_bounty_trustless` — create with escrow, claim, submit, approve, payout
2. `test_create_bounty_hitm` — create with HITM, claim, submit, approve, payout
3. `test_funding_verification_fail` — create without payment should revert
4. `test_auto_release_hitm_timeout` — submit, wait, auto-release
5. `test_reject_and_revise` — create, claim, submit, reject, revise, approve, payout
6. `test_max_rejections_abandoned` — create, claim, submit, reject (3x), claim_abandoned
7. `test_dispute_resolution` — create, claim, submit, dispute, resolve(agent_win/creator_win)
8. `test_dispute_timeout` — create, claim, submit, dispute, wait 30d, timeout_dispute, split payout
9. `test_claim_timeout` — create, claim, wait 48h, expire_claim, bounty reopened
10. `test_invalid_state_transitions` — claim from CLOSED, approve from OPEN, etc.
11. `test_rekey_protection` — ensure RekeyTo is rejected
12. `test_proof_data_validation` — oversized proof data rejected
13. `test_github_oidc_bridge` — github_verify then set_github_status
14. `test_esa_funding` — ASA-based bounty with asset transfer verification
15. `test_timeout_dispute_split` — create, claim, submit, dispute, wait 30d, timeout_dispute → 50/50 split
16. `test_github_oidc_flow` — github_verify → set_github_status("pass") → approve_work
17. `test_get_bounty_info` — verify logged output structure
18. `test_half_amount_split` — verify escrow_amount/2 for odd amounts (integer division)

---

## 10. Deployment Steps

```bash
# 1. Compile
algokit compile escrow.algo -o escrow.teal

# 2. Test
algokit test --root tests/ --test-files test_escrow_contract.py

# 3. Deploy to TestNet
algokit deploy escrow.algo --env .env.testnet

# 4. Verify on AlgoExplorer
algokit explore --verify escrow.teal
```

---

## 11. Known Constraints

### 11.1 Escrow Funding Requires Group Transaction

The creator MUST include the escrow payment in the same group as the `create_bounty()` call. This is a fundamental constraint of the Algorand AVM — the app account cannot receive funds on its own; they must arrive in a group transaction.

**Workaround:** The client (AlgoKit, dApp frontend, or Gateway API) assembles the group atomically. Most clients handle this transparently.

### 11.2 Contract Cannot Initiate Payments

The smart contract cannot send funds by itself. A payout requires:
- The contract to approve the state transition (AppCall)
- A payment transaction in the same group (signed by the contract's rekeyed account or multisig)
\nThis means the creator must either:
- Keep the contract rekeyed to their own account (recommended), OR
- Use a multisig/DAO for governance-based fund release

### 11.3 DISPUTED_TIMEOUT State (v2)

The `DISPUTED_TIMEOUT` state (value 6) is reserved for the `timeout_dispute()` method which transitions to `CLOSED` with `payout_type = SPLIT`. In the current implementation, the transition goes directly to `CLOSED` with `SPLIT` type. The state value exists for future expansion (e.g., adding intermediate UI states or audit logging).

---

*Document version: 4.0 | Created: 2026-06-30 | Synced with escrow.algo source | Security features: escrow funding verification, actual payout execution model, dispute/claim timeouts, GitHub OIDC bridge, read-only bounty info method*
