# Legal #173: Platform Fee — Unenforced Rate — Revenue Classification

**GitHub Issue:** https://github.com/IcanBENCHurCAT/algo-bounty/issues/173
**Status:** In Progress (Pipeline Recovery)

## Problem
The platform fee (2%) is constitutional but has no enforcement mechanism in the smart contract or gateway. The revenue stream classification is also undefined — is it service fee, commission, or royalty? This affects tax treatment and legal liability.

---

## SPECKIT DECOMPOSITION

### 🟢 Research

- **R173-1 — Fee Collection Audit:** Read the current escrow contract and gateway code. Trace where the 2% fee is calculated vs where it actually goes. Identify the gap: is it deducted from escrow? Paid separately? Lost to floating-point rounding? Output: fee trace diagram.
- **R173-2 — Revenue Classification Research:** Research US SaaS/commission revenue classification for AI agent platforms. Is AlgoBounty's fee a "service fee" (SaaS model), "commission" (broker model), or "royalty" (IP model)? This determines tax form (1099-K vs 1099-MISC). Output: classification memo.

### 🔵 Design

- **D173-1 — Fee Enforcement Architecture:** Design the on-chain fee enforcement. Options: (a) Deduct at escrow creation (simpler, less fraud), (b) Deduct at payout (more complex, but allows escrow disputes without fee issues), (c) Hybrid — partial at creation, partial at payout. Recommend (c). Output: contract spec + fee flow diagram.
- **D173-2 — Fee Split Design:** Based on ADR 0002 (superseded by ADR 0012), the 2% is split 50/50 between Developer Royalty and Platform Treasury. Design the on-chain inner payment transaction that splits the fee at payout. Output: TEAL/PyTeal code for the fee split logic.
- **D173-3 — Fee Classification in DB:** Add `revenue_classification` to the platform config. This is a single value (service_fee | commission | royalty) that controls how fees appear on receipts and determines tax reporting. Output: DB migration for `platform_config` column.

### 🟠 Build

- **B173-1 — Fee Deduction at Escrow:** Modify escrow creation to deduct the platform fee (2% of escrow amount) at the time of funding. The fee goes to the platform treasury address. Verify the remaining escrow matches the creator's intent.
- **B173-2 — Fee Deduction at Payout:** At payout (success or dispute resolution), apply the remaining 0% (since 2% was taken at creation) or the correct split if using the hybrid model. Ensure the split goes: 1% to Developer Royalty, 1% to Platform Treasury.
- **B173-3 — Fee Visibility Endpoint:** Add `GET /api/v1/bounties/{id}/fees` that returns a breakdown of all fees for a specific bounty (platform fee, developer royalty, mediator fee, total). This is for transparency and dispute resolution.
- **B173-4 — Admin Fee Dashboard:** Add a `/admin/fees` view showing total fees collected (platform vs developer), breakdown by date, and any fee disputes.

### 🟣 Test

- **T173-1 — Unit: Fee Calculation:** Test that a $100 escrow results in $2 platform fee deduction. Verify the worker receives 100% of the principal (fee is separate). Test edge cases: minimum escrow, maximum escrow.
- **T173-2 — Unit: Fee Split:** Test that the 2% fee is correctly split: 1% → Developer Royalty, 1% → Platform Treasury. Verify PyTeal inner payment transactions execute correctly.
- **T173-3 — Integration: Full Fee Flow:** Create escrow ($100) → fee deducted → claim → complete → payout → verify 1% each to royalty/treasury → verify worker gets full $100.

### ⚪ Deploy

- **DPL173-1 — Update Escrow Contract:** Deploy the updated escrow contract with fee enforcement. Note the contract version in changelog.
- **DPL173-2 — Fee Classification Set:** Set the `revenue_classification` to `service_fee` (most defensible for an AI platform). This will be used for tax reporting.
- **DPL173-3 — Monitor Fee Flow:** Track fee collection for 72 hours. Verify all fees are being deducted and routed correctly. Alert if >0.1% of transactions have fee discrepancies.

---

**Total: 16 subtasks (2 research, 3 design, 4 build, 3 test, 3 deploy)**
**Estimated effort: 2-3 hours**
