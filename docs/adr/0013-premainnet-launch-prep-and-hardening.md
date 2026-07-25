# v13: Pre-Mainnet Launch Preparation & Final Hardening

This document details the architectural decisions made during the implementation of the Pre-Mainnet Launch Preparation & Final Hardening feature (`003-premainnet-launch-prep`).

---

## Status
Approved / Implemented

## Context & Problem
Before launching AlgoBounty on Mainnet, the platform required four final hardening steps identified by the Council of Three architectural review:
1. Smart contract platform fees needed to be parameterizable dynamically per bounty creation call (`platform_fee` Box storage) so fee rates can be tuned without modifying frozen PyTEAL approval bytecode schemas.
2. An automated 30-day dispute fallback (`timeout_dispute()`) was needed to ensure smart contract immutability never results in permanently frozen escrow funds.
3. Operating dispute resolutions and account quarantines via CLI `curl` commands presented high operational risks, requiring a visual `/admin` dashboard portal.
4. Non-custodial software provider disclaimers, Federal Arbitration Act (FAA) arbitration waivers, and Phase 1 stewardship rules required explicit user consent via a mandatory Terms of Service (ToS) modal.

## Decision
1. **Dynamic Platform Fee Parameterization**: Added `self.platform_fee = Box(UInt64, key="platform_fee")` in `escrow.py`. `create_bounty()` validates $1 \le \text{platform\_fee} \le 1000$ (max 10.0%) and stores fee basis points per escrow instance. `_send_payout_with_royalties()` reads `platform_fee` from box storage, preserving 100% TEAL bytecode immutability across deployments.
2. **30-Day Automated Dispute Fallback**: Updated `timeout_dispute()` in `escrow.py` to enforce a 30-day ($2,592,000$ seconds) timeout. If a dispute remains unacted upon for 30 days, any participant can trigger a trustless 50/50 split resolution on-chain.
3. **Dedicated Admin Dashboard Portal**: Created `/admin` in Next.js `dashboard/` protected by `ADMIN_ADDRESS` wallet authentication. Provides visual tabs and 1-click action buttons for **Disputed Bounties** (`Worker Win`, `Creator Win`, `50/50 Split`) and **Account Quarantines** (`Clear Quarantine`, `Penalize -100 Karma`).
4. **Mandatory Terms of Service Modal**: Implemented `TermsModal.tsx` in `dashboard/` disclaiming custodial software status, establishing FAA arbitration waivers, and detailing Phase 1 stewardship rules. Consent is persisted in `localStorage`.

## Consequences
- **Positive**:
  - Smart contract PyTEAL bytecode is 100% frozen, audited, and immutable.
  - Funds can never be permanently trapped in escrow, even if keys are lost or panels deadlock.
  - Administrative operations are visual, safe, and instantaneous via the `/admin` portal.
  - Non-custodial legal disclaimers protect the core entity against MSB classification and bailment liabilities.
- **Negative**:
  - Requires `ADMIN_ADDRESS` wallet configuration in environment variables for portal access.

## Superseded Decisions
- **ADR 0001 (TEAL Escrow Contract)**: Parameterized platform fees override hardcoded `TemplateVar[UInt64]("PLATFORM_FEE")` literals in approval TEAL.
