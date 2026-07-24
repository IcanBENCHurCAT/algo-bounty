# Quickstart: Validating the Fee Split Feature

**Feature**: 006-fee-split-payouts
**Purpose**: Runnable validation scenarios that prove the 50/50 fee split works end-to-end.

## Prerequisites

1. AlgoBounty project cloned at `/home/st9797/.openclaw/workspace/algo-bounty`
2. Python 3.11+ with `py-algorand-sdk`, `algopy`, `puya` installed (see `requirements.txt`)
3. A local Algorand node or sandbox (e.g., `algod` running locally)
4. Test accounts with ALGO balance (or access to testnet)

## Compilation

```bash
cd /home/st9797/.openclaw/workspace/algo-bounty
python compile_teal.py
```

Expected output:
- `EscrowContract.approval.teal` — compiled approval program
- `EscrowContract.clear.teal` — compiled clear program
- `EscrowContract.arc56.json` — ARC56 application specification

Verify compilation succeeds without errors. Any compilation errors are a failure condition.

## Validation Scenarios

### VS-001: Approve Work Payout — Fee Split Verification

**Setup**:
1. Deploy the `EscrowContract` on a local sandbox.
2. Create a bounty: fund 1,000 ALGO escrow, assign a mediator and treasury.
3. Claim the bounty as agent A.
4. Submit work by agent A.
5. Approve work as creator.

**Expected Outcome**:
- App call returns `work_approved` log.
- State transitions to `CLOSED` with `payout_type = PAYOUT`.
- Exactly 4 inner payment transactions emitted:
  1. `10 ALGO` → creator (developer royalty, 1%)
  2. `10 ALGO` → treasury (platform treasury, 1%)
  3. `2 ALGO` → mediator (0.25%)
  4. `978 ALGO` → agent (97.8%)

**Verification command** (pseudo):
```python
# After approve_work() call, inspect the app return events and inner txn count
assert inner_txn_count == 4
assert inner_txns[0].receiver == creator_address
assert inner_txns[0].amount == 10
assert inner_txns[1].receiver == treasury_address
assert inner_txns[1].amount == 10
assert inner_txns[2].receiver == mediator_address
assert inner_txns[2].amount == 2
assert inner_txns[3].receiver == agent_address
assert inner_txns[3].amount == 978
assert sum(txn.amount for txn in inner_txns) == 1000  # total distributed = escrow_amount
```

---

### VS-002: Creator Win Dispute — Royalty Dedup

**Setup**:
1. Create a bounty (1,000 ALGO).
2. Claim and submit work.
3. Creator submits dispute.
4. Mediator resolves as "creator_win" with valid signature.

**Expected Outcome**:
- State → `CLOSED`, `payout_type = REFUND`.
- Exactly 3 inner payment transactions (royalty deduplicated):
  1. `10 ALGO` → treasury (1%)
  2. `2 ALGO` → mediator (0.25%)
  3. `978 ALGO` → creator (97.75% + 1% royalty = same as total refund)

**Verification**:
```python
assert inner_txn_count == 3  # royalty deduped
assert inner_txns[0].receiver == treasury_address
assert inner_txns[0].amount == 10
assert inner_txns[1].receiver == mediator_address
assert inner_txns[1].amount == 2
assert inner_txns[2].receiver == creator_address
assert inner_txns[2].amount == 978
assert sum(txn.amount for txn in inner_txns) == 1000
```

---

### VS-003: Arbitrator Vote — Agent Win

**Setup**:
1. Create bounty (1,000 ALGO).
2. Claim, submit work, dispute.
3. Arbitrators vote (consensus agent_win).

**Expected Outcome**:
- State → `CLOSED`, `payout_type = PAYOUT`.
- 4 inner payments: creator(10), treasury(10), arbitrator(s), agent(978).
- Arbitrator fees come from the 5% arbitration fee pool (not the 2% fee split).

---

### VS-004: Auto-Release HITM — Post-Deadline

**Setup**:
1. Create bounty with `is_hitm=1`, review_days=0 (immediate deadline).
2. Claim and submit work.
3. Advance timestamp past deadline.
4. Call `auto_release()`.

**Expected Outcome**:
- State → `CLOSED`, `payout_type = PAYOUT`.
- 4 inner payments same as VS-001 (royalty, treasury, mediator, agent).

---

### VS-005: Micro-Payout — 100 ALGO Floor Division

**Setup**: Create bounty with 100 ALGO escrow. Fund, claim, submit, approve.

**Expected Outcome**:
- `fee_total = 100 * 2 // 100 = 2`
- `royalty = 2 // 2 = 1`
- `treasury = 2 - 1 = 1`
- `mediator = 100 * 25 // 10000 = 2`
- `agent = 100 - 2 - 2 = 96`

Verification:
```python
assert inner_txns[0].amount == 1   # creator royalty
assert inner_txns[1].amount == 1   # treasury
assert inner_txns[2].amount == 2   # mediator
assert inner_txns[3].amount == 96  # agent
assert sum == 100                  # total = escrow
```

---

### VS-006: Tampered Payout Rejection

**Setup**: Attempt to call `approve_work()` while manipulating the inner transaction amounts (e.g., by modifying the gateway to send wrong amounts).

**Expected Outcome**: The contract should reject the transaction because:
- The fee split amounts are computed on-chain in `_send_fee_split()` — not passed as parameters.
- The amounts are computed directly from `escrow_amount`, making them deterministic and tamper-proof.

**Verification**: This is inherently verified by the implementation — since amounts are computed inside the contract (not accepted as parameters), the gateway cannot alter them. Any attempt to send wrong amounts would require modifying the TEAL bytecode itself.

---

### VS-007: Non-ALGO ASA Payout

**Setup**: Create bounty with `asset_id > 0` (e.g., USDC). Fund with ASA, claim, submit, approve.

**Expected Outcome**: Same split ratios apply using ASA amounts:
- Creator: 1% of ASA escrow
- Treasury: 1% of ASA escrow
- Mediator: 0.25% of ASA escrow
- Agent: 97.75% of ASA escrow

---

### VS-008: All Existing Tests Pass

**Command**:
```bash
cd /home/st9797/.openclaw/workspace/algo-bounty
python -m pytest tests/ -v
```

**Expected**: All existing unit and integration tests pass without modification. The fee split changes should not affect non-payout code paths (creation, claim, submission, dispute, vote).

## Run Order

1. Compile: `python compile_teal.py`
2. Run VS-008 first (baseline): `python -m pytest tests/ -v` — confirms nothing is broken
3. Add new test cases for VS-001 through VS-007
4. Run the full suite: `python -m pytest tests/ -v` — all pass

## Manual Inspection

After each test payout, inspect the Algorand node logs or indexer:
```bash
# Check app logs for the new payout_type
# Verify 4 inner txn count in approved app calls
# Confirm all inner txns use fee=0
# Verify amounts match the fee split formula
```
