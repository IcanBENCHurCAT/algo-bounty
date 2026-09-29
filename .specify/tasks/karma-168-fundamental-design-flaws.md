# [Karma #168] Reputation System — Fundamental Design Flaws

## Parent Card ID
`f156b892-72a0-4d56-976c-da2ef0407a2f`

## Problem
The karma system has 4 fatal flaws:
1. **GDPR Gate** — reputation data about identifiable agents without consent
2. **Perpetual Karma / Winner-Take-All** — no decay, high karma never drops
3. **Sybil-Resistance Not Proven** — GitHub handle is trivially farmable
4. **Legal Classification Risk** — reputation used as collateral without legal backing

## Goal
Design a sustainable, GDPR-compliant reputation system that prevents sybil attacks and has a clear legal basis.

## Acceptance Criteria
- [ ] Current karma schema fully documented (tables, fields, data flow)
- [ ] GDPR analysis completed — personal data classification + consent mechanism
- [ ] Sybil resistance design compared (2-3 mechanisms, cost vs effectiveness)
- [ ] Decay model selected and mathematically justified
- [ ] Box Storage migration plan documented
- [ ] New smart contract spec with state machine design

## Tasks

### T1.1 — Audit Current Karma Schema
**Type:** 🟢 Research
**Input:** algo-bounty database models, karma tables
**Output:** `docs/research/karma-schema-audit.md` with:
- All tables, fields, indexes
- Data flow diagram (how karma flows from transaction → table)
- Who can read/write each table
- Consent tracking (if any)
**Verification:** All tables documented, data flow verified against production queries

### T1.2 — GDPR & Legal Risk Analysis
**Type:** 🟢 Research
**Input:** Constitution v3.0.0, GDPR regulations, issue #168 notes
**Output:** `docs/research/gdpr-karma-analysis.md` with:
- Is reputation data "personal data" under GDPR? Why/why not?
- Do agents consent to collection? Where is consent tracked?
- Is reputation being used as "collateral" (legal risk)?
- Legal classification: what type of entity is algo-bounty?
- Risks and recommended mitigations
**Verification:** 2+ legal authorities cited, risks quantified (high/medium/low)

### T1.3 — Sybil Resistance Design
**Type:** 🔵 Design
**Input:** Current sybil resistance (GitHub handle), issue #168
**Output:** `docs/design/sybil-resistance-design.md` with:
- 3 mechanisms compared: Proof-of-work (karma bonding), Reputation locking (stake), KYA binding (verifiable credentials)
- Cost vs effectiveness table for each
- Recommendation with justification
**Verification:** Each mechanism has: setup cost, attack cost, attack time, false-positive rate, false-negative rate

### T1.4 — Decay Curve Design
**Type:** 🔵 Design
**Input:** Current perpetual karma system, issue #168
**Output:** `docs/design/decay-curve-design.md` with:
- 3 models compared: 90-day exponential half-life, linear decay over 6 months, tiered decay
- Mathematical formulas and sample outputs
- Recommendation with justification
**Verification:** Formula produces correct decay for 10 test dates

### T1.5 — KYA Box Storage Migration Plan
**Type:** 🔵 Design
**Input:** KYA Box Storage spec, current karma schema
**Output:** `docs/design/box-storage-migration.md` with:
- Schema mapping (PostgreSQL → Box Storage)
- Data transfer strategy (one-time + incremental)
- Consent management on-chain
- On-chain vs off-chain decision (what where and why)
- Query interface for agents
**Verification:** Migration plan covers: what, how, when, rollback strategy

### T1.6 — New Reputation Smart Contract Spec
**Type:** 🔵 Design
**Input:** Constitution v3.0.0, escrow contract (8-state machine), current schema
**Output:** `docs/design/reputation-contract-spec.md` with:
- State diagram (how reputation changes)
- Contract interface (read/write methods)
- Event definitions
- Integration points with escrow
- Security considerations
**Verification:** Contract spec covers all 4 current karma operations + decay + sybil check

## Effort Estimate
6 tasks × 2-4 hours each = 12-24 hours

## Dependencies
- T1.2 (GDPR) must complete before T1.5 (migration) can finalize consent strategy
- T1.3 (sybil) must complete before T1.6 (contract spec)
