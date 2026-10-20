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
