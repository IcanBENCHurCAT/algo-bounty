# Quickstart Validation Guide: Phase 1 Pre-Mainnet Hardening

**Date**: 2026-07-25
**Feature**: [spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/002-phase1-hardening/spec.md)

## Prerequisites

- Python 3.12+ with virtual environment activated
- Node.js 18+ (for dashboard)
- AlgoKit LocalNet running (`algokit localnet start`)
- Gateway dependencies installed (`pip install -r requirements.txt`)
- Dashboard dependencies installed (`cd dashboard && npm install`)
- Environment: `TESTING=True`, `ALGORAND_NETWORK=sandbox`

## Validation Scenarios

### VS-001: State Machine — Escalation After Max Rejections

**Proves**: FR-001 (auto-transition to disputed after MAX_REJECTIONS)

```bash
# Run the state machine escalation test
PYTHONPATH=. python -m pytest tests/test_evaluators.py -v -k "test_escalate_to_dispute_after_max_rejections"
```

**Expected outcome**: Test creates a bounty, submits work, rejects 3 times, then the worker calls `escalate_to_dispute()` and the state transitions to `DISPUTED`. Attempting `claim_abandoned()` before the timeout fails.

---

### VS-002: Refund Lock — Refund Blocked from SUBMITTED State

**Proves**: FR-002 (refund blocked from SUBMITTED), FR-003 (refund allowed from CLAIMED/OPEN)

```bash
PYTHONPATH=. python -m pytest tests/test_evaluators.py -v -k "test_refund_blocked_from_submitted"
```

**Expected outcome**: A bounty in SUBMITTED state cannot have funds reclaimed by the creator via any method. A bounty in CLAIMED state (before work submission) can be refunded after claim expiry.

---

### VS-003: Manual GitHub Sync & Pull Payout

**Proves**: FR-004 (manual sync), FR-005 (worker pull), FR-006 (idempotency)

```bash
# Start the gateway
PYTHONPATH=. python gateway/main.py &

# Test sync endpoint
PYTHONPATH=. python -m pytest tests/test_sync_github.py -v
```

**Expected outcomes**:
1. `POST /api/v1/bounties/{id}/sync-github` detects a merged PR and sets `payout_ready=True`.
2. `POST /api/v1/bounties/{id}/claim-payout` by the worker triggers fund release.
3. A second sync for the same PR merge returns `already_processed`.
4. A non-worker calling `claim-payout` gets 403.

---

### VS-004: Evaluator Rename — Zero Arbitrator References

**Proves**: FR-007 (user-facing rename), FR-008 (DB rename), SC-004 (zero instances)

```bash
# Check user-facing code for "arbitrator" references
grep -riI "arbitrator" gateway/ dashboard/src/ --include="*.py" --include="*.ts" --include="*.tsx" | grep -v "__pycache__" | grep -v "node_modules"
```

**Expected outcome**: Zero matches. All references should now use "evaluator".

```bash
# Verify API endpoint responds
curl http://localhost:8000/api/v1/evaluators
# Should return 200 with evaluator list

curl http://localhost:8000/api/v1/arbitrators
# Should return 404 or redirect
```

---

### VS-005: Admin Dispute Resolution

**Proves**: FR-009 (admin stewardship), FR-010 (admin resolution interface)

```bash
PYTHONPATH=. python -m pytest tests/test_admin_disputes.py -v
```

**Expected outcomes**:
1. A dispute routed to the admin returns an admin notification.
2. Admin can call `POST /api/v1/admin/disputes/{id}/resolve` with `{resolution: "worker_win"}` and the bounty is closed with worker payout.
3. A non-admin calling the endpoint gets 403.

---

### VS-006: Quarantine System

**Proves**: FR-011 (quarantine state), FR-012 (notification), FR-013 (admin review), FR-014 (auto-expiry)

```bash
PYTHONPATH=. python -m pytest tests/test_quarantine.py -v
```

**Expected outcomes**:
1. Triggering a quarantine blocks the account from creating new bounties.
2. `GET /api/v1/account/quarantine-status` shows quarantine details.
3. Admin can clear the quarantine via `POST /api/v1/admin/quarantines/{id}/resolve`.
4. After 72 hours (simulated), the quarantine auto-expires.

---

### VS-007: Refund Lock Documentation

**Proves**: FR-015 (creation notice), FR-016 (detail view indicator), FR-017 (ToS)

```bash
# Start the dashboard
cd dashboard && npm run dev &

# Visual check — navigate to bounty creation page
# Verify refund lock notice is visible during funding step
# Navigate to a bounty with submitted work
# Verify escrow lock indicator is displayed
```

**Expected outcome**: A prominent notice appears during bounty creation warning that escrowed funds cannot be refunded once work is submitted. Bounties with submitted work show a lock indicator.

---

## Full Test Suite

```bash
# Run all Phase 1 hardening tests
PYTHONPATH=. python -m pytest tests/test_evaluators.py tests/test_sync_github.py tests/test_quarantine.py tests/test_admin_disputes.py -v

# Verify zero "arbitrator" references in codebase
grep -riI "arbitrator" gateway/ dashboard/src/ escrow.py --include="*.py" --include="*.ts" --include="*.tsx" | grep -v "__pycache__" | grep -v "node_modules" | wc -l
# Expected: 0
```
