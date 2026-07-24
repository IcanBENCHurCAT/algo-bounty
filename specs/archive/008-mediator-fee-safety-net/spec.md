# Feature Specification: Dynamic Mediator Fee Safety Net

**Feature Branch**: `008-mediator-fee-safety-net`

**Created**: 2026-07-18

**Status**: Draft

**Input**: User description: "/speckit-specify features needed to fill the gaps in our constitution update"

---

## 1. Executive Summary & Context

This feature implements the **Mediator Fee Safety Net** rules established in Version 2.1.0 of the AlgoBounty Project Constitution. Under the previous contract design, a `0.25%` mediator fee was unconditionally deducted from the bounty escrow and sent to the mediator address on every payout (even under HITM mode or undisputed Auto mode). 

This specification defines the architectural changes required across the smart contract, backend gateway, and frontend dashboard to dynamically redistribute the `0.25%` fee allocation to the worker when no mediation occurs, and split it evenly among mediators only when mediation is active.

---

## 2. User Scenarios & Testing

### User Story 1 — HITM Mode Fee Redirection (Priority: P1)
As Alice (a Project Creator), I want to create a bounty in Human-in-the-Middle (HITM) mode, knowing that since no mediators can participate, the mediator fee allocation will be given to the worker to maximize their incentive.

* **Why this priority**: Core MVP requirement to ensure creators aren't paying idle fees when doing manual reviews.
* **Independent Test**: Deploy the contract in HITM mode, execute a successful work approval, and assert that the claimant payout equals `escrow_amount - platform_fees` (with `0%` mediator fee deduction).
* **Acceptance Scenarios**:
  1. **Given** a bounty is created with `is_hitm = 1`,
     **When** the creator approves the submission via `approve_work`,
     **Then** the `0.25%` mediator fee is added to the claimant's payment, and `0 ALGO` is sent to the mediator account.

---

### User Story 2 — Undisputed Auto Mode Fee Redirection (Priority: P1)
As Bob (a Worker), I want to claim and complete an Auto-mode (non-HITM) bounty, knowing that if Alice approves my work without raising a dispute, I will receive the mediator fee allocation as a reward.

* **Why this priority**: Essential to encourage smooth worker collaborations and prevent protocol fee leakage.
* **Independent Test**: Deploy an Auto-mode bounty, submit work, approve it without dispute, and verify on-chain that the `0.25%` mediator fee is paid to the worker.
* **Acceptance Scenarios**:
  1. **Given** a bounty has `is_hitm = 0` (Auto mode),
     **When** the creator approves the work without initiating a dispute,
     **Then** the contract transfers `escrow_amount - platform_fees` to the claimant (including the `0.25%` mediator fee allocation).

---

### User Story 3 — Disputed Auto Mode Fee Split (Priority: P2)
As a Mediator, I want to resolve a dispute on an Auto-mode bounty, knowing that the `0.25%` mediator fee will be distributed to active mediators who arbitrate.

* **Why this priority**: Correctly funds and incentivizes decentralized dispute resolution.
* **Independent Test**: Initiate a dispute, call `resolve_dispute`, and verify that the `0.25%` fee is split among the active mediators.
* **Acceptance Scenarios**:
  1. **Given** an Auto-mode bounty enters a dispute,
     **When** the dispute is resolved via `resolve_dispute`,
     **Then** the `0.25%` mediator fee is sent to the mediator address (or split evenly among voting mediators if multi-mediator is active).

---

### User Story 4 — Dynamic Fee Display in Frontend UI (Priority: P1)
As Alice or Bob, I want to see a real-time, accurate breakdown of fees in the dashboard before posting or claiming, reflecting these dynamic safety net rules.

* **Why this priority**: Critical for visual clarity and alignment with Constitution §6.1.
* **Independent Test**: Load the `/create` and `/bounties/[bounty_id]` pages in the browser and assert that the fee table dynamically updates the mediator fee row to `0 ALGO (Redirected)` under HITM or undisputed states.
* **Acceptance Scenarios**:
  1. **Given** the creator is on the `/create` form with HITM toggled ON,
     **Then** the `FeeBreakdownTable` displays the mediator fee row as `0 ALGO (Redirected to worker)`.
  2. **Given** a worker is viewing an open Auto-mode bounty details page,
     **Then** the `FeeBreakdownTable` displays the mediator fee as `0 ALGO (Paid to worker if undisputed)`.

---

## 3. Requirements

### 3.1 Functional Requirements
* **FR-001 (Smart Contract Fee Routing)**: Modify `_send_fee_split` in `escrow.py` to evaluate the bounty review mode (`self.is_hitm`) and the dispute status.
* **FR-002 (HITM Redirection)**: If `is_hitm == 1`, redirect the `fee_mediator` payout to the claimant/worker.
* **FR-003 (Undisputed Auto Redirection)**: If `is_hitm == 0` and the contract is settled via normal approval (`approve_work` or timeout approval) without entering dispute, redirect the `fee_mediator` payout to the claimant/worker.
* **FR-004 (Dispute Fee Transfer)**: If dispute resolution is triggered (`resolve_dispute`), payout the `fee_mediator` directly to the mediator account.
* **FR-005 (Frontend Hook Calculation)**: Update [useFeeBreakdown.ts](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/dashboard/src/hooks/useFeeBreakdown.ts) and components to correctly compute and show the dynamically adjusted fee structure.
* **FR-006 (Gateway API Estimation)**: Align the backend gateway's fee breakdown estimators to return identical values.

---

## 4. Edge Cases

* **No claimant assigned (refund case)**: If the creator requests a refund because a bounty was never claimed, the mediator fee should not be charged. The full escrow amount is returned to the creator (minus standard platform deposit fees).
* **Multi-mediator arbitration**: If future scope includes multiple arbitrators, the mediator fee must be split equally among the addresses registered in the dispute vote state.
