# Legal #171: Bounty Terms — Missing Legal Enforceability

**GitHub Issue:** https://github.com/IcanBENCHurCAT/algo-bounty/issues/171
**Status:** In Progress (Pipeline Recovery)

## Problem
The platform terms of service are constitutional description, not enforceable contracts. Users have no DB-backed acceptance record, no versioning, no governing law, and no dispute/blacklist flow.

---

## SPECKIT DECOMPOSITION

### 🟢 Research

- **R171-1 — Audit Current ToS:** Read the live ToS on the gateway and extract every clause. Compare against the constitution v3.0.0 for gaps. Output: a gap analysis table (ToS clause → Constitution section → Present/Absent → Enforceable?)
- **R171-2 — Jurisdiction Scan:** Identify which jurisdiction(s) AlgoBounty operates under. Check constitution for any governing law clause. If missing, document the risk (US? offshore? no jurisdiction?).

### 🔵 Design

- **D171-1 — Acceptance Flow Design:** Design a DB-backed user acceptance model. When does a user become bound? On first claim? On first escrow? Or on explicit "I agree" click? Output: sequence diagram + DB schema for `user_terms_acceptance` table (user_id, terms_version, accepted_at, ip_hash).
- **D171-2 — Versioning Schema:** Design terms versioning. Each ToS revision gets a version number + effective date. Users who don't re-accept at the next revision are flagged but not auto-kicked. Output: migration plan for Supabase schema.
- **D171-3 — Governing Law + Arbitration Clause:** Draft the governing law clause (e.g., Delaware, USA) and a mandatory arbitration clause that overrides small-claims courts. This needs to be a separate Terms-of-Service document, not embedded in the constitution. Output: drafted clause text.
- **D171-4 — Dispute + Blacklist Flow:** Design the flow: if a user is banned (fraud, sanctions), the gateway blocks their address from new bounties. If a user disputes, they get a 48h window before the gateway can freeze their active bounties. Output: flow diagram.

### 🟠 Build

- **B171-1 — DB Schema Migration:** Create and run the Supabase migration that adds `user_terms_acceptance` table with columns: id, user_id (FK to users), terms_version (string), accepted_at (timestamp), ip_hash (string). Add index on (user_id, terms_version).
- **B171-2 — Terms Endpoint:** Add `POST /api/v1/terms/accept` that records acceptance. Body: `{ "version": "1.0" }`. Returns 201 + the full ToS text at that version.
- **B171-3 — Terms GET Endpoint:** Add `GET /api/v1/terms/current` that returns the current active version + text. Add `GET /api/v1/terms/{version}` for historical lookup.
- **B171-4 — Enforcement Middleware:** Add a middleware layer in the bounty creation/claim endpoints that checks `user_terms_acceptance` for the user. If missing or version mismatch → return 451 "Terms Not Accepted" with the current ToS text and a link to accept.
- **B171-5 — Blacklist Endpoint:** Add `POST /api/v1/users/{id}/blacklist` (admin only) and `GET /api/v1/users/{id}/blacklist` (status check). Blacklisted addresses are blocked from creating bounties.

### 🟣 Test

- **T171-1 — Unit: Acceptance Records:** Test the `POST /terms/accept` endpoint. Verify DB record is created, returns 201, and subsequent claims succeed. Test that duplicate acceptance is idempotent (no error).
- **T171-2 — Unit: Enforcement Middleware:** Test that a user without accepted terms gets 451 on bounty creation. Test that a user with accepted terms gets 200. Test version mismatch behavior.
- **T171-3 — Integration: Full Flow:** Create a test user → create bounty (should 451) → accept terms → create bounty (should succeed) → verify DB record.
- **T171-4 — Blacklist Flow:** Blacklist a test user → verify they can't create new bounties → whitelist → verify they can.

### ⚪ Deploy

- **DPL171-1 — Migration Execution:** Run the Supabase migration in production. Verify the table is created with correct schema.
- **DPL171-2 — Gate New Bounties:** Enable the enforcement middleware in production. Add a grace period (24h) before it becomes hard-block, so existing users have time to accept.
- **DPL171-3 — Monitoring:** Add metrics for "terms acceptance rate" and "enforcement blocks". Alert if >10% of users are hitting 451 after the grace period.

---

**Total: 16 subtasks (2 research, 4 design, 5 build, 4 test, 3 deploy)**
**Estimated effort: 2-3 hours**
