# Quickstart Validation Guide: Pre-Mainnet Launch Preparation

This guide documents runnable validation scenarios to prove fee parameterization, admin dashboard portal, and Terms of Service modal functionality.

---

## Scenario 1: Smart Contract Fee Parameterization Validation

### Run Smart Contract Unit Tests
```bash
PYTHONPATH=. python -m pytest tests/test_fee_split.py -v
```

### Expected Outcome
- Smart contract accepts dynamic `platform_fee` parameters (e.g. 150 bps = 1.5%).
- Inner transactions disburse exactly 1.5% to Treasury and 98.5% to Worker.
- Fee basis points > 1000 trigger assertion panic.

---

## Scenario 2: Admin Dashboard Portal Validation

### 1. Start Gateway API & Dashboard Server
```bash
# Start Gateway
export PYTHONPATH=.
python gateway/main.py

# Start Next.js Dashboard
cd dashboard && npm run dev
```

### 2. Verify Admin Portal Access
- Open `http://localhost:3000/admin` in browser with non-admin wallet $\to$ Expect **403 Forbidden** banner ("Administrator access required").
- Connect wallet matching `ADMIN_ADDRESS` $\to$ Access granted. Tabs for "Active Disputes" and "Account Quarantines" render.
- Click "Worker Win" on a disputed bounty $\to$ Backend processes `POST /api/v1/admin/disputes/{id}/resolve` and updates UI state to `closed`.

---

## Scenario 3: Terms of Service Modal Validation

### 1. Clear Local Storage
Open Browser DevTools Console on `http://localhost:3000` and execute:
```javascript
localStorage.removeItem("algobounty_tos_accepted");
```

### 2. Connect Wallet & Verify Modal
- Click "Connect Wallet" on dashboard layout.
- **Expected Outcome**: `TermsModal` opens displaying non-custodial software disclaimers, FAA arbitration clauses, and best-effort stewardship rules.
- Click "Accept & Continue" $\to$ Modal closes, `algobounty_tos_accepted` set to `"true"` in `localStorage`, and normal user actions proceed.
