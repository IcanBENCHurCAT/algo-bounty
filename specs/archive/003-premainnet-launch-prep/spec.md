# Feature Specification: Pre-Mainnet Launch Preparation & Final Hardening

**Feature Branch**: `003-premainnet-launch-prep`  
**Created**: July 25, 2026  
**Status**: Draft  
**Input**: User description: "Parameterize platform fees in escrow.py so fee percentages can be tuned without bytecode redeployment. Build a dedicated /admin management page in dashboard/ for dispute resolution and account quarantine reviews. Publish mandatory Terms of Service (ToS) disclaimers clarifying non-custodial software status and best-effort pre-mainnet dispute resolution. To ensure contract immutability never results in permanently frozen funds (e.g. if an Admin key is lost or an Evaluator panel deadlocks), add a 30-day automated dispute fallback in escrow.py that allows a 50/50 split resolution if a dispute remains unacted upon for 30 days."

---

## User Scenarios & Testing

### User Story 1 - Smart Contract Platform Fee Parameterization (Priority: P1)

As a platform operator, I want platform fee basis points (`PLATFORM_FEE`) in `escrow.py` to be dynamically parameterizable during bounty contract deployment so that platform fee percentages can be tuned or set per deployment without needing to modify or redeploy contract bytecode schemas.

**Why this priority**: Immutability requires that contract bytecode schemas are locked before Mainnet deployment. Parameterizing fee basis points allows fee adjustments across newly deployed escrow instances while keeping the core PyTEAL approval bytecode 100% frozen and immutable.

**Independent Test**: Deploy an escrow instance passing a custom fee rate (e.g. 150 basis points = 1.5%), simulate work approval, and verify that the inner transaction disburses exactly 1.5% to the Treasury and 98.5% to the primary recipient.

**Acceptance Scenarios**:

1. **Given** a new bounty deployment transaction, **When** `create_bounty()` is called with `platform_fee` set to 150 basis points, **Then** the contract stores 150 in box storage or template variable and disburses 1.5% to the Treasury upon payout.
2. **Given** a bounty payout approval, **When** `approve_work()` is called, **Then** inner transactions calculate `fee_amount = (escrow_val * platform_fee) // 10000` with integer loss prevention.

---

### User Story 2 - Dedicated Admin Management Portal (Priority: P1)

As a platform administrator, I want a dedicated `/admin` management interface in the Next.js `dashboard/` so that I can visually review open disputes, inspect GitHub PR diffs, execute 1-click dispute resolutions (`Worker Win`, `Creator Win`, `Split`), and review/resolve account quarantines without resorting to CLI `curl` commands.

**Why this priority**: Operational stewardship during Phase 1 requires real-time visibility into disputes and flagged accounts. A dedicated admin portal eliminates manual CLI errors and ensures high-priority disputes are resolved within SLA windows.

**Independent Test**: Log into `dashboard/` using the configured `ADMIN_ADDRESS` wallet, navigate to `/admin`, view active disputes and quarantines, click "Resolve Dispute (Worker Win)", and verify the bounty state updates to `closed` with `PAYOUT`.

**Acceptance Scenarios**:

1. **Given** an authenticated user whose wallet matches `ADMIN_ADDRESS`, **When** navigating to `/admin`, **Then** the Admin Management Dashboard renders showing active disputes and active quarantines.
2. **Given** a non-admin wallet, **When** navigating to `/admin`, **Then** access is denied with a 403 Forbidden notice ("Administrator access required").
3. **Given** an active dispute card on `/admin`, **When** clicking "Worker Win", "Creator Win", or "Split" with a resolution note, **Then** the backend executes `POST /api/v1/admin/disputes/{id}/resolve` and updates the bounty state.
4. **Given** an active account quarantine card on `/admin`, **When** clicking "Clear Quarantine" or "Penalize", **Then** the backend updates the quarantine record and restores creation privileges if cleared.

---

### User Story 3 - Mandatory Terms of Service & Non-Custodial Legal Disclaimers (Priority: P1)

As a user (Creator or Worker) connecting my Algorand wallet, I want to review and accept mandatory Terms of Service (ToS) disclaimers clarifying that AlgoBounty is non-custodial software, dispute resolution during Phase 1 is a best-effort pre-mainnet stewardship service, and financial compliance/taxes are direct counterparty responsibilities.

**Why this priority**: Mitigates regulatory classification risks (FinCEN MSB/Money Transmitter) and protects the core project entity against bailment/custodial liability by establishing explicit legal consent and arbitration waivers under the Federal Arbitration Act (FAA).

**Independent Test**: Connect a fresh wallet in `dashboard/`, verify the ToS modal appears on first action, accept the terms, and confirm `localStorage` persists acceptance so subsequent interactions proceed seamlessly.

**Acceptance Scenarios**:

1. **Given** a first-time user connecting a wallet, **When** initiating bounty creation or claim actions, **Then** a Terms of Service modal is presented disclaiming custodial liability and explaining Phase 1 best-effort admin stewardship.
2. **Given** the ToS modal, **When** the user clicks "Accept & Continue", **Then** terms agreement is recorded and the user can proceed with protocol actions.

---

### User Story 4 - 30-Day Automated Dispute Fallback (Priority: P1)

As a protocol participant (Creator or Worker), I want a 30-day automated dispute fallback in `escrow.py` (`resolve_dispute_timeout()`) so that if an Admin key is lost or an Evaluator panel deadlocks, any participant can trigger a 50/50 split resolution after 30 days of dispute inactivity, ensuring escrow funds are never permanently frozen on-chain.

**Why this priority**: Immutability guarantee. Guaranteeing an automated, trustless exit path for deadlocked disputes eliminates single-point-of-failure risks and prevents permanent capital lockup.

**Independent Test**: Advance block timestamp by 30 days ($2,592,000$ seconds) on a disputed bounty, invoke `resolve_dispute_timeout()`, and verify the contract disburses a 50/50 split to Creator and Worker and closes the contract.

**Acceptance Scenarios**:

1. **Given** a bounty in `DISPUTED` state, **When** fewer than 30 days have elapsed since `dispute_timestamp`, **Then** calling `resolve_dispute_timeout()` panics with "30-day dispute timeout has not elapsed".
2. **Given** a bounty in `DISPUTED` state, **When** block timestamp exceeds `dispute_timestamp + 2592000`, **Then** calling `resolve_dispute_timeout()` disburses a 50/50 split and closes the escrow contract.

---

## Key Entities

- **FeeConfig**: Stores `platform_fee` basis points (default: 200 = 2.0%, max: 1000 = 10.0%) for escrow fee calculations.
- **AdminSession**: Authenticated state for `ADMIN_ADDRESS` in the dashboard UI.
- **TermsAgreement**: Local and database record verifying wallet address consent to protocol ToS.
- **DisputeTimeoutConfig**: `DISPUTE_TIMEOUT = 2592000` (30 days in seconds) fallback guard.

---

## Functional Requirements

- **FR-001**: Smart contract `escrow.py` MUST accept and store `platform_fee` basis points dynamically per bounty creation call.
- **FR-002**: Smart contract inner transaction fee payouts MUST use `(escrow_val * platform_fee) // 10000` with integer loss prevention.
- **FR-003**: Smart contract MUST implement `resolve_dispute_timeout()` permitting 50/50 split execution after $2,592,000$ seconds in `DISPUTED` state.
- **FR-004**: Gateway API `POST /api/v1/admin/disputes/{id}/resolve` MUST accept resolution decisions from authenticated `ADMIN_ADDRESS` JWTs.
- **FR-005**: Gateway API `GET /api/v1/admin/quarantines` and `POST /api/v1/admin/quarantines/{id}/resolve` MUST provide quarantine listing and resolution controls for admins.
- **FR-006**: Next.js dashboard MUST provide a dedicated route `/admin` accessible only to the authenticated `ADMIN_ADDRESS`.
- **FR-007**: Admin dashboard `/admin` MUST display tabs for "Disputed Bounties" and "Account Quarantines" with detailed action cards.
- **FR-008**: Next.js dashboard MUST present a Terms of Service modal disclaiming custodial escrow status and explaining Phase 1 stewardship rules.
- **FR-009**: Navigation layout MUST show an "Admin" link in the sidebar when the connected wallet matches `ADMIN_ADDRESS`.
- **FR-010**: Backend MUST enforce maximum platform fee bounds ($\le 1000$ basis points / 10%).

---

## Success Criteria

- **SC-001**: 100% of smart contract unit tests pass with parameterized fee basis points (e.g. 100, 150, 200 bps).
- **SC-002**: `resolve_dispute_timeout()` executes successfully after 30 days and fails prior to 30 days.
- **SC-003**: Admin portal `/admin` loads active disputes and quarantines in $< 500\text{ms}$ and executes 1-click resolutions cleanly.
- **SC-004**: 0 non-admin users can access `/admin` UI or invoke `/api/v1/admin/*` endpoints (returns 403 Forbidden).
- **SC-005**: 100% of first-time wallet connects encounter the ToS disclaimer modal before executing transactions.
