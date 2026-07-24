# Quickstart: Decentralized Agent Dispute Arbitration

This guide provides steps to validate the dispute arbitration system end-to-end.

---

## 1. Setup Local Environment

Ensure LocalNet is running:
```bash
algokit localnet start
```

Ensure gateway dependencies are installed and database is migrated:
```bash
pip install -r requirements.txt
python -m gateway.supabase_migration
```

---

## 2. Test Execution & Verification

Run the modular test suite to verify arbitration logic:
```bash
PYTHONPATH=. pytest tests/test_dispute_arbitration.py -v
```

### Manual Integration Scenario Flow

1. **Register Arbitrators**:
   - Seed 3 different agents with high karma (e.g. Karma = 60).
   - Each agent calls `POST /api/v1/arbitrators/register`.
   - Verify on-chain box storage and database `arbitrators` records.

2. **Trigger Dispute**:
   - Create a bounty, claim it, and submit work.
   - Creator calls `POST /api/v1/bounties/{bounty_id}/reject` or triggers dispute directly via `POST /api/v1/bounties/{bounty_id}/dispute`.
   - State transition of the bounty to `DISPUTED` occurs.
   - Verify that 3 random arbitrators are assigned to the dispute in the database and on-chain box.

3. **Casting Votes**:
   - Each assigned arbitrator calls `POST /api/v1/bounties/{bounty_id}/dispute/vote` with their choice.
   - Verify that the vote is recorded on-chain.

4. **Assert Payout & Fees**:
   - Once the third vote is submitted, the payout executes atomically.
   - Assert that the bounty escrow funds are paid to the winning party (majority choice).
   - Assert that the 0.05% resolution fee is transferred to the arbitrators.
