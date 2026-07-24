# Research: Node Incentivization & Fee Splitting

## Decision 1: Gateway Address Storage & Registration Method

### Options Considered
- **Option A**: Modify `create_bounty` signature to `create_bounty(byte[],uint64,uint64,uint64,uint64,address,address,address)void` to accept `gateway_address` directly.
- **Option B**: Introduce a separate, optional ABI method `set_gateway_address(address)void` that can be called by the bounty creator.

### Selection & Rationale
Based on user feedback ("no need to maintain backwards compat"), we select **Option A**.
* **Rationale**: Directly passing `gateway_address` as a parameter to `create_bounty` simplifies the workflow to a single transaction during bounty creation. It removes the complexity of having a separate setup transaction call.
* **Storage**: We will add a new box `gateway_address` of type `Account` (32 bytes) populated directly during `create_bounty`.

---

## Decision 2: Fee Splitting Logic in Payouts

### Rules & Requirements
- Platform fee: 2% of the total payout.
- If `gateway_address` is registered (and is not the zero address):
  - 1% is sent to Developer Royalty (creator's address).
  - 0.5% is sent to the central Treasury.
  - 0.5% is sent to the registered `gateway_address`.
- If `gateway_address` is NOT registered (or zero address):
  - 1% is sent to Developer Royalty (creator's address).
  - 1% is sent to the central Treasury.
- The 0.25% mediator fee remains unaffected and subject to the existing mediator safety net.
