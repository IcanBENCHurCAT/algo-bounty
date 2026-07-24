# Feature Specification: Platform Fee Splits Pre-Signed Validation in Web3 UX

**Feature Branch**: `007-fee-split-ux`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "User Story 2: Platform Fee Splits Pre-Signed Validation in Web3 UX (Priority: P2) — Update the Next.js frontend wallet connector flow to dynamically calculate and explicitly display the fee split amounts (Developer Royalty vs. Platform Treasury) in the Web3 modal before the creator signs the transaction. Align with Constitution Rule 6.1 (Least-Privilege visibility). Acceptance: Given a creator is reviewing a completed bounty for approval, when they click 'Approve Payout', the approval modal displays a breakdown: Total Released, Developer Royalty (1%), Platform Funding (1%), Claimant Payout. Given a wallet signature prompt, when the transaction group is built, the generated ABI method call arguments match the calculations displayed in the UX."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Fee Split Display on Approve Payout (Priority: P2)

When a creator navigates to a submitted bounty and clicks "Approve & Release," a confirmation modal must appear that explicitly shows how the escrowed funds will be distributed: the 1% developer royalty (to the creator themselves), the 1% platform treasury fee, the 0.25% mediator fee (if applicable), and the remaining claimant payout. The creator must review and confirm this breakdown before the transaction is signed by their wallet.

**Why this priority**: Constitution Rule 6.1 mandates that the frontend MUST display clear, legible transaction details before requesting a wallet signature. Hidden side effects are strictly prohibited. While the contract enforces the split on-chain, users need off-chain visibility to maintain trust and understand where their funds are routing before signing. This is a trust-and-transparency UX requirement, not a technical dependency.

**Independent Test**: A submitted bounty can be opened by its creator, who clicks "Approve & Release." The confirmation modal appears with a fee breakdown table. The displayed amounts can be verified against the escrow amount shown on the page. Dismissing the modal returns the user to the bounty detail page without any transaction being signed or sent.

**Acceptance Scenarios**:

1. **Given** a bounty of 1,000 ALGO is in the `submitted` state and the creator is viewing the bounty detail page, **When** the creator clicks "Approve & Release," **Then** a confirmation modal appears showing: Total Released (1,000 ALGO), Developer Royalty (10 ALGO / 1%), Platform Treasury (10 ALGO / 1%), Mediator Fee (2.5 ALGO / 0.25%, if HITM), and Claimant Payout (977.5 ALGO).
2. **Given** the approval modal is displayed with the fee breakdown, **When** the creator clicks "Confirm & Sign," **Then** the wallet signature prompt is shown with the transaction group pre-populated, and the generated ABI method call arguments match the calculations displayed in the modal.
3. **Given** the approval modal is displayed, **When** the creator clicks "Cancel" or closes the modal, **Then** no transaction is signed, no request is sent to the gateway, and the user returns to the bounty detail page.

---

### User Story 2 — Fee Split Display on Dispute Resolution (Priority: P3)

When a dispute is resolved (either through mediator resolution, auto-resolution, timeout, or arbitration), the fee split breakdown should also be shown before the creator or agent signs the resolution transaction, so both parties understand the final distribution.

**Why this priority**: Transparency applies to all fund-disbursement flows, not just creator approvals. Mediators, agents, and creators involved in dispute outcomes need visibility into where funds are going before signing.

**Independent Test**: A disputed bounty can be auto-resolved or manually resolved. The resolution transaction triggers a confirmation modal showing the fee split for that specific payout type (PAYOUT, REFUND, or SPLIT).

**Acceptance Scenarios**:

1. **Given** a bounty is in the `submitted` state with HITM enabled and the review deadline has passed, **When** the auto-release path triggers (or a manual resolution is initiated), **Then** the fee split breakdown modal displays for the signing party with amounts specific to the resolution type.
2. **Given** a bounty dispute is resolved via arbitration with a split outcome, **When** the split transaction is built, **Then** the modal shows: Total, Developer Royalty, Platform Treasury, Mediator Fee, Arbitrator Fee (5%), and each party's half of the remainder.

---

### Edge Cases

- **Zero or negligible fees**: What happens when the escrow amount is so small that 1% rounds to 0 ALGO via integer division? The modal should still display the breakdown (e.g., "Developer Royalty: 0 ALGO") to maintain transparency.
- **Non-HITM bounties**: No mediator fee is deducted. The modal should only show: Total, Developer Royalty, Platform Treasury, and Claimant Payout (no mediator line).
- **Refund flows**: When funds are refunded to the creator, the fee split is NOT applied. The modal should indicate "No fees deducted — full refund" rather than showing a fee breakdown.
- **Split payouts**: When a dispute timeout or arbitration split sends funds to both creator and agent, the modal should clearly label each recipient's share.
- **Gateway API returns fee estimate**: The backend API endpoint for building the approve transaction should include a `fee_breakdown` object in its response so the frontend can display pre-computed values without duplicating the contract's calculation logic.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The approve payout flow on the bounty detail page MUST display a confirmation modal before invoking the wallet signature prompt.
- **FR-002**: The approval modal MUST display a fee breakdown table showing: Total Escrow Amount, Developer Royalty (1% of escrow), Platform Treasury (1% of escrow), Mediator Fee (0.25% of escrow, only when HITM is enabled), and Claimant Payout (remaining balance after fees).
- **FR-003**: The fee amounts displayed in the modal MUST be computed using the same integer-division floor logic as the smart contract to ensure the on-chain and off-chain values match exactly.
- **FR-004**: The gateway API endpoint that returns the unsigned approve transaction MUST also return a `fee_breakdown` object containing the computed fee amounts (royalty, treasury, mediator, claimant) so the frontend can display them without local calculation.
- **FR-005**: The modal MUST have a "Confirm & Sign" action and a "Cancel/Close" action. Clicking "Cancel" must NOT trigger any transaction or API call.
- **FR-006**: When the creator clicks "Confirm & Sign," the wallet signature prompt MUST be shown with the pre-built transaction group (app call + payment inner transactions) matching the displayed fee breakdown.
- **FR-007**: For non-HITM bounties, the mediator fee line MUST be omitted from the breakdown table.
- **FR-008**: For dispute resolution flows (arbitration, timeout, auto-resolution), the modal MUST adapt its breakdown labels to match the payout type (PAYOUT, REFUND, SPLIT) and include arbitrator fees where applicable.
- **FR-009**: The confirmation modal MUST be accessible (WCAG 2.1 AA compliant) with proper labels, keyboard navigation, and ARIA attributes for screen readers.
- **FR-010**: All fee display values MUST be formatted as human-readable amounts in ALGO (not micro-ALGO), with appropriate decimal precision (integer for whole numbers, 2 decimal places for amounts under 1 ALGO).

### Key Entities

- **Fee Breakdown**: A structured object containing the computed fee amounts for a given escrow payout: `royalty`, `treasury`, `mediator`, `arbitrator`, `claimant`, each as a number in ALGO.
- **Approval Modal**: A UI overlay component shown before wallet signature, displaying the fee breakdown and requiring explicit confirmation.
- **Unsigned Transaction Response**: The API response object returned by `getApproveTxn`, extended to include `fee_breakdown` alongside the existing `unsigned_txn`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of approve-payout transactions show the fee breakdown modal before wallet signature.
- **SC-002**: Zero instances where the fee amounts displayed in the modal differ from the amounts sent on-chain (verified by comparing frontend display values against the actual transaction group submitted).
- **SC-003**: All dispute resolution flows (PAYOUT, REFUND, SPLIT) display an appropriate fee breakdown or "no fees" message.
- **SC-004**: The approval modal renders correctly on mobile viewports (screen width ≤ 480px) with all fee breakdown information visible without horizontal scrolling.

## Assumptions

- The smart contract's `_send_fee_split()` helper (implemented in feature #006) is already deployed and computes fees using the same integer-division formula: `royalty = treasury = escrow * 2 // 100 // 2`, `mediator = escrow * 25 // 10000`, `claimant = escrow - royalty - treasury - mediator`.
- The existing `getApproveTxn` API endpoint can be extended to include a `fee_breakdown` field without requiring a new endpoint.
- The `signTransaction` flow (handled by the wallet provider) is already integrated and does not need modification — we only need to show the breakdown before calling it.
- The frontend uses the existing wallet connection context (`useAuth` hook) and follows the same modal/dialog pattern already established in the codebase for disputes.
- The gateway's `escrow.py` already exposes the escrow amount and fee calculation results to the API layer; the gateway may need a small addition to return `fee_breakdown` in the approve-txn response.
