# Deployment TODO

**IMPORTANT: NO deployment was performed in this change set.**

## What Changed and Why
1. **F3 Typed-Client Wiring Complete**: F3 typed-client wiring is complete at all three call sites (`get_claim_txn`, `get_approve_txn`, `release_trustless`); no redeploy required or performed.
2. **Rekey Guard Gap Fixed**: Added `assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))` to the following methods in `escrow.py`: `auto_resolve_creator_win`, `timeout_dispute`, `auto_release`, `expire_claim`, and `delete_bounty`. This closes an account-takeover vector via permissionless timer methods, bringing the code into compliance with Constitution rule 2.3.
2. **AVM-12 Compliance**: Updated the compilation target for `escrow.py` to AVM 12 (`#pragma version 12`) in compliance with Constitution rule 2.1. Generated corresponding artifacts.
3. **Readme Updates**: Fixed Constitution rule references and Next.js version badging.

## Redeploy Checklist for Future Deployment
- [ ] Recompile `escrow.py` and verify artifacts (TEAL, arc56.json, arc32.json) are up to date and correct.
- [ ] Deploy the updated smart contract to TestNet first.
- [ ] Run all automated tests against the TestNet deployment.
- [ ] Perform any manual QA against the TestNet deployment.
- [ ] Deploy the validated smart contract to MainNet.
- [ ] Update the App ID registry (e.g. backend environment variables or frontend configuration) to point to the new MainNet App ID.
- [ ] Verify the new App ID is functioning correctly on-chain.

## 2026-10-28: Escrow security fixes (issues #214, #215, #216) - NO deployment performed
- **#214**: `approve_work` now asserts `state == SUBMITTED` before paying out (was callable from CLAIMED/REJECTED/DISPUTED, and from OPEN where the payout went to the zero address).
- **#215**: `github_verify` and `set_github_status` now require the gateway as sender; `set_github_status` also requires SUBMITTED. `github_verify` stores its data in new dedicated boxes (`github_pr_url`, `github_test_hash`) instead of overwriting the agent's `proof_url`/`proof_data`.
- **#216**: `auto_resolve_creator_win` now pays the fee-split remainder returned by `_send_fee_split` instead of the full `escrow_amount` on top of the fees.
- Artifacts regenerated with puyapy 5.10.1 (AVM 12) using the same invocations that reproduce the previous artifacts byte-for-byte on the old source: TEAL with PLATFORM_FEE=200, arc56 without it, per-network timeout template vars.
- Still to do at deploy time (in addition to the checklist above):
  - [ ] Regenerate typed clients from the new arc56 (`gateway/EscrowContractClient.py`, `dashboard/src/lib/EscrowContractClient.ts`).
  - [ ] Regenerate or retire `artifacts/EscrowContract.arc32.json` (legacy format).
  - [ ] Root-level `EscrowContract.arc56.json` / `*.puya.map` were already stale relative to source before this change; regenerate or remove.
  - [ ] Gateway box references for `github_verify`/`set_github_status` calls must include the new `github_pr_url` / `github_test_hash` boxes.
