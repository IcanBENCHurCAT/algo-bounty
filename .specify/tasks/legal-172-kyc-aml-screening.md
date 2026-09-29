# Legal #172: KYC/AML — No Address Screening Before Escrow

**GitHub Issue:** https://github.com/IcanBENCHurCAT/algo-bounty/issues/172
**Status:** In Progress (Pipeline Recovery)

## Problem
KYC/AML screening happens nowhere; anyone can escrow from a fresh address. The platform collects 2% fees and holds funds in escrow but has no mechanism to know who those funds belong to or if they're from sanctioned addresses.

---

## SPECKIT DECOMPOSITION

### 🟢 Research

- **R172-1 — KYA API Audit:** Read the KYA (Know Your Agent) service API documentation. Identify which endpoints support sanctions screening (OFAC, UN, EU lists), address risk scoring, and identity verification. Output: API capability matrix.
- **R172-2 — Regulatory Trigger Analysis:** Determine which legal triggers apply. Does a fresh address holding >$10,000 equivalent in escrow require KYC? What about $1,000? Check US FinCEN rules and EU MiCA for digital asset thresholds. Output: threshold table with required action at each level.

### 🔵 Design

- **D172-1 — Screening Integration Point Design:** Design where KYA screening happens in the flow. Options: (a) At wallet connect, (b) At first escrow, (c) At first claim. Recommend (a) + progressive: soft-screen at connect, hard-screen at first escrow > threshold. Output: sequence diagram.
- **D172-2 — Risk Tier Schema:** Design risk tiers based on KYA results. Tier 1 (green): standard access. Tier 2 (yellow): enhanced monitoring, lower escrow limits. Tier 3 (red): blocked, manual review. Output: database schema for `kyc_risk_tiers` table.
- **D172-3 — Progressive KYC Flow:** Design the progressive KYC flow. Users can start with just their wallet address (low-risk screening). If they hit escrow thresholds or trigger sanctions flags, they go to enhanced KYC (name, DOB, jurisdiction). Output: state machine.

### 🟠 Build

- **B172-1 — KYA Screen Endpoint:** Create `POST /api/v1/kyc/screen` that takes an Algorand address, calls KYA, and returns a risk score + sanctions flag. Caches result for 24h.
- **B172-2 — Sanctions Block Middleware:** Add middleware to escrow creation that calls the KYA screen and blocks if `sanctions_match=true`. Returns 403 with the sanctions list name.
- **B172-3 — Risk Tier Integration:** Wire up the `kyc_risk_tiers` table. When KYA returns a tier, update the user's tier. Update escrow limits based on tier (e.g., Tier 2: max $5,000 escrow; Tier 3: $0).
- **B172-4 — Admin Dashboard View:** Add a `/admin/kyc` view showing flagged users, their risk tier, sanctions matches, and actions (approve/block).

### 🟣 Test

- **T172-1 — Unit: KYA Integration:** Mock the KYA API. Test screen returns green/yellow/red for different risk profiles. Test cache behavior (second call within 24h returns cached result).
- **T172-2 — Unit: Sanctions Block:** Test that a sanctions-matched address gets 403 on escrow creation. Test that a clean address proceeds normally.
- **T172-3 — Integration: Full KYC Flow:** Create user → connect wallet → screen (green) → create escrow → success. Then: create user → connect wallet → screen (red) → create escrow → blocked.

### ⚪ Deploy

- **DPL172-1 — KYA API Key Setup:** Verify the KYA API key is configured in production secrets.
- **DPL172-2 — Enable Soft-Screen:** Deploy the soft-screen at wallet connect first. No blocking, just logging. Monitor for false positives.
- **DPL172-3 — Enable Hard-Screen:** After 24h of soft-screen validation, enable the hard-screen on escrow creation. Start with a high threshold ($10,000) and work down.

---

**Total: 15 subtasks (2 research, 3 design, 4 build, 3 test, 3 deploy)**
**Estimated effort: 2 hours**
