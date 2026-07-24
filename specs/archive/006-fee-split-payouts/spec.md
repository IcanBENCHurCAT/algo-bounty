# Feature Specification: Programmatic 50/50 Fee Split on Payouts

**Feature Branch**: `006-fee-split-payouts`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Modify the AVM smart contract (escrow.algo) and payout orchestration to split the 2% fee collected during bounty completion. 1% is sent to the Developer Royalty address, and 1% is sent to the Platform Treasury account."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Automatic Split Payout on Bounty Approval (Priority: P1)

When a bounty is approved for payout and the escrow contract executes the distribution, the 2% platform fee collected from the escrowed amount is automatically split 50/50 on-chain: half goes to the Developer Royalty address (the bounty creator), and half goes to the Platform Treasury account. The claim submitter receives the remaining 98% of the escrowed amount.

**Why this priority**: This is the core revenue-sharing mechanism required by the AlgoBounty Constitution (Section 5.3). Without it, the platform collects fees but does not distribute them per its own governance rules. This change is required for all bounty payout flows.

**Independent Test**: A single escrow can be funded, claimed, submitted, and approved. The payout can then be verified by inspecting the three resulting payment transactions (creator royalty, platform treasury, claimant) and confirming the amounts sum correctly.

**Acceptance Scenarios**:

1. **Given** a bounty of 1,000 ALGO is funded and approved for payout, **When** the payout transaction group is executed by the contract, **Then** the contract executes three inner payment transactions: 10 ALGO (1%) to the Developer Royalty address, 10 ALGO (1%) to the Platform Treasury address, and 980 ALGO (98%) to the claim submitter.
2. **Given** a payout transaction group, **When** the contract verifies the payment distribution, **Then** it rejects the entire group if the split ratio is altered or destination addresses do not match those set at contract creation.
3. **Given** a bounty escrow in ALGO Asset (non-ALGO ASA), **When** the payout is processed, **Then** the same 50/50 fee split logic applies using the same asset type, with correct amounts proportional to the escrowed quantity.
4. **Given** a micro-payout of 100 ALGO, **When** the 2% fee is computed (2 ALGO), **Then** each recipient receives 1 ALGO and the claimant receives 98 ALGO — confirming integer-division floor behavior is acceptable for the smallest supported escrow.

---

### Edge Cases

- What happens when the 2% fee is so small that floor division yields 0 ALGO for both split recipients? (The claimant should still receive the full remaining amount.)
- How does the contract handle a re-keyed creator address when computing the royalty destination at payout time vs. creation time?
- What if the Platform Treasury address is the same as the creator address? The contract should still emit two separate payment transactions (or handle deduplication gracefully).
- How are dispute refunds affected? If the bounty is refunded/disputed and funds return to escrow, no fee split should occur on the refund path — only on the final successful payout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The smart contract MUST split the 2% platform fee into two equal 1% portions: one routed to the Developer Royalty address and one to the Platform Treasury address.
- **FR-002**: Both the Developer Royalty address and the Platform Treasury address MUST be stored as on-chain box fields at contract creation time.
- **FR-003**: The payout logic (all exit paths that release remaining escrow funds to the claimant) MUST execute a trio of inner payment transactions in a single atomic group: royalty, treasury, and claimant.
- **FR-004**: The contract MUST verify that the inner transaction group contains exactly three payment transactions and that their amounts sum to the total escrow balance being distributed.
- **FR-005**: The contract MUST reject the payout transaction group if any inner payment amount deviates from the expected 50/50/98 split ratio.
- **FR-006**: The contract MUST reject the payout if the destination addresses in the payment transactions do not match the stored Developer Royalty and Platform Treasury addresses.
- **FR-007**: Refund and dispute-resolution paths MUST NOT trigger any fee split — only successful payout completions invoke the split logic.
- **FR-008**: The off-chain payout orchestration layer MUST construct and submit the atomic transaction group containing the app call and the three inner payments, without any modification to the amounts or recipients.
- **FR-009**: All three payment transactions in the payout group MUST use `fee=0` (paying fees from the sender account) to minimize transaction cost overhead.
- **FR-010**: The platform fee split ratio (50/50 of the 2% fee) MUST be configurable only by the platform administrator/multi-sig/DAO per Constitution rule 5.2, and any change MUST go through the full spec-kit process.

### Key Entities

- **Developer Royalty Address**: The wallet address of the bounty creator, stored at escrow creation. Receives 50% of the 2% fee (i.e., 1% of escrow amount).
- **Platform Treasury Address**: The platform's treasury account, set at contract deployment. Receives 50% of the 2% fee (i.e., 1% of escrow amount).
- **Claimant**: The agent or worker who submitted the bounty proof and is receiving the remaining 98% payout.
- **Escrow Amount**: The total funded amount locked in the escrow account, from which the 2% fee is computed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successful bounty payouts execute the three-transaction split (royalty, treasury, claimant) with correct fee proportions.
- **SC-002**: Zero successful payout transactions where the fee split deviates from the configured ratio — all violations are rejected on-chain.
- **SC-003**: Zero payout transactions where funds are sent to an address not matching the stored Developer Royalty or Platform Treasury addresses.
- **SC-004**: All existing tests (unit and integration) pass after the fee split logic is integrated, confirming no regression in non-payout code paths (creation, claim, submission, dispute, refund).

## Assumptions

- The 2% fee base is already computed correctly at the top of each payout flow in the existing contract (current behavior: `escrow_amount * 2 // 100`). This feature modifies only the *destination* of that fee, not its rate.
- The Developer Royalty address is the same as the bounty creator's address (as defined at escrow creation time).
- Integer division via floor (`//`) is acceptable for fee amounts; any sub-ALGO remainder is absorbed by the claimant.
- The off-chain gateway/payout orchestrator already knows both the Developer Royalty address (from the escrow box data) and the Platform Treasury address (from contract globals).
- The constitution's Section 5.3 fee-sharing rule is authoritative and does not require additional business justification.
