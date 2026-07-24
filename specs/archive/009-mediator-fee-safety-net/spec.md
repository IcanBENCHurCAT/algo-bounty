# Feature Specification: Hosted Indexer Neutrality & Compliance Disclaimers

**Feature Branch**: `009-mediator-fee-safety-net`

**Created**: 2026-07-18

**Status**: Draft

**Input**: User description: "/speckit-specify the needed changes"

---

## 1. Executive Summary & Context

This feature implements the **Hosted Indexer Neutrality** policies (Constitution §5.6), **Direct Peer-to-Peer Engagement** tax disclosures (Constitution §5.7), and **Stewardship of Autonomous Agents** rules (Constitution §5.8).

It accomplishes two primary goals:
1. **Regulatory De-risking (Indexer & UI)**: Removes treasury-fee filtering from the backend indexer, allows creators to override platform fee percentages and treasury destinations in the UI, and incorporates direct P2P tax liability and agent human-stewardship disclaimers.
2. **Indexer and Database Overrides**: Updates database tables to store and display custom fee rates and treasury targets.

---

## Clarifications

### Session 2026-07-18
- Q: To support indexer neutrality, the indexer must crawl all deployments even if they override default platform fees and treasury addresses. Should we persist these custom overrides (`platform_fee` and `treasury_address`) in our database schema? → A: Update SQLAlchemy and Supabase database models to store the customized platform fee rate and treasury address per bounty.
- Q: When the project creator sets a custom platform fee override during bounty creation, should we enforce an upper limit/cap on this fee? → A: Enforce a maximum platform fee cap of 10% in the smart contract validation logic and frontend input form.
- Q: Are the P2P tax liability and agent stewardship disclaimers in the UI strictly mandatory to check before a user can proceed? → A: Strictly mandatory. Users cannot connect their wallet or submit the bounty creation form without checking both disclaimers.
- Q: Do we need to persist or log the user's acceptance of the disclaimers on the backend database or blockchain? → A: Purely frontend validation. The checked state is validated locally before allowing actions and is not stored in the database or on-chain.
- Q: To maintain hosted indexer neutrality (Constitution §5.6), how should we handle potential spam or malicious contracts? Should the indexer perform any filtering? → A: Allow basic security/spam filtering (e.g. valid contract schemas), but strictly forbid filtering based on fee structures or treasury destinations.

---

## 2. User Scenarios & Testing

### User Story 1 — Custom Treasury & Platform Fee Overrides (Priority: P1)
As Alice (a Project Creator), I want to override the default platform fee parameters and set the treasury destination to a custom address (or set it to `0%` fee), and see my bounty successfully displayed on the marketplace dashboard.

* **Why this priority**: Prevents hosted indexers from being classified as commercial matching brokers.
* **Independent Test**: Deploy an escrow contract with `platform_fee = 0%` and a custom treasury address, verify it is successfully indexed and displayed on the marketplace dashboard.
* **Acceptance Scenarios**:
  1. **Given** Alice posts a bounty with custom fees,
     **When** the backend indexer crawls the block,
     **Then** it registers the bounty details in the directory database regardless of fee structure.

---

### User Story 2 — P2P Tax & Agent Stewardship Disclaimers (Priority: P1)
As a user connecting my wallet or creating a bounty, I want to see clear disclaimers explaining that all tax compliance is handled off-chain directly between creators and workers, and that agent accounts must register a human steward, so I am aware of my compliance obligations.

* **Why this priority**: Essential to align with Constitution §§5.7-5.8.
* **Independent Test**: Trigger the "Connect Wallet" flow and assert that the disclaimer is displayed.
* **Acceptance Scenarios**:
  1. **Given** a user opens the wallet connection dropdown or bounty creation page,
     **Then** the UI displays the P2P tax liability and Agent Human-Stewardship notice.

---

## 3. Requirements

### 3.1 Functional Requirements
* **FR-001 (Indexer Generalization)**: Remove treasury address filtering or indexing restrictions from `gateway/indexer.py` to neutrally show all matching deployments.
* **FR-002 (Custom Fee UI Fields)**: Expand the `/create` bounty form to support setting custom platform fees and treasury addresses.
* **FR-003 (Dashboard Legal Checklist)**: Display tax liability and agent stewardship checkboxes in the wallet connection and bounty creation flows.
* **FR-004 (Database Model Updates)**: Update the database models (SQLAlchemy/Supabase) to store the customized platform fee rate and treasury address per bounty.
* **FR-005 (Custom Fee Validation Cap)**: Enforce a maximum custom platform fee cap of 10% in the smart contract validation logic and frontend input form.
* **FR-006 (Mandatory UI Checkboxes)**: Make the P2P tax liability and agent stewardship checkboxes strictly mandatory before connecting a wallet or submitting the bounty creation form.
* **FR-007 (Frontend-only Disclaimer Validation)**: The disclaimer acceptance state is validated purely on the frontend (local state/storage) and not persisted in the DB or on-chain.
* **FR-008 (Indexer Spam Filtering)**: Ensure the indexer allows basic security/spam filtering of non-conforming application schemas, but strictly forbid filtering based on fee structures or treasury destinations.
