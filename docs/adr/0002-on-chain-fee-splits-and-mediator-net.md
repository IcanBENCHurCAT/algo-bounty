# ADR 0002: On-Chain Fee Splits & Mediator Safety Net

**Date**: 2026-07-19

**Status**: Accepted

## Context
The platform collects a 2% fee on successful bounty payouts and an additional 0.25% fee reserved for mediators. To align with the AlgoBounty Constitution (Specs 006, 007, and 008) regarding revenue sharing, decentralization, and transparency, the fee mechanics and user experience must be defined clearly. Specifically:
- The 2% platform fee needs to be distributed according to governance rules (50% to Developer Royalty, 50% to Platform Treasury).
- The 0.25% mediator fee should not become dead capital or platform profit when a mediator is not needed (e.g., Human-in-the-Middle mode or undisputed Auto mode).
- Users must understand exactly how their escrowed funds are being split before signing transactions.

## Decision
1. **On-Chain 50/50 Fee Split**: The 2% base platform fee will be programmatically split on-chain during the payout transaction group. 1% will be sent to the Developer Royalty address (AlgoBounty creator) and 1% will be sent to the Platform Treasury account.
2. **Dynamic Mediator Fee Redirection (Safety Net)**: 
   - If the bounty is in HITM mode (`is_hitm = 1`), the 0.25% mediator fee is redirected entirely to the worker/claimant.
   - If the bounty is in Auto mode (`is_hitm = 0`) and is resolved without entering a dispute, the 0.25% fee is also redirected to the worker/claimant.
   - The fee is only sent to the mediator address if an active dispute resolution occurs.
3. **Pre-Signed Web3 UX Transparency**: The frontend must present an explicit breakdown of all fees (Total, Developer Royalty, Platform Treasury, Mediator Fee, Claimant Payout) in a confirmation modal *before* requesting a wallet signature. The API will pre-calculate this breakdown to match the contract's integer-division logic.

## Consequences
- **Positive**: Creates strong incentives for workers (bonus for undisputed work) and creators (royalty sharing). Guarantees absolute transparency and aligns the smart contract with the platform's constitutional revenue-sharing model.
- **Negative**: Increases the complexity of the payout transaction group (requires 3 distinct inner payment transactions). The frontend must maintain complex state to accurately reflect the smart contract's integer-floor math to prevent display discrepancies.
