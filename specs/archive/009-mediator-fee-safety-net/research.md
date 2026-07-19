# Research: Dynamic Mediator Fee Safety Net & Indexer Neutrality

This document outlines the architectural decisions, design rationale, and alternatives considered for implementing the Mediator Fee Safety Net and Hosted Indexer Neutrality features.

---

## 1. Database Overrides for Custom Fees and Treasuries

* **Decision**: Add `platform_fee` (integer basis points, e.g., 200 for 2%) and `treasury_address` (string/address) columns to the `bounties` table in SQLAlchemy models (`gateway/supabase_migration.py`) and Supabase PostgreSQL schema.
* **Rationale**: To support indexer neutrality, the gateway must be capable of indexing and serving bounties that utilize custom fee splits and destinations. Persisting these fields directly on the bounty record allows fast marketplace queries, rendering, and filtering, rather than requesting global state from the Algorand node on every dashboard request.
* **Alternatives Considered**: 
  * *On-chain Queries Only*: Querying the Algorand node directly for the global state of each application upon request. Rejected due to latency and rate-limit constraints when rendering marketplace feeds.
  * *Default Fallback in API*: Hardcoding default values in the API and only storing overrides. Rejected because storing the explicit values for every bounty simplifies the query logic and ensures historical accuracy if platform defaults change.

---

## 2. Custom Fee Validation Cap (10%)

* **Decision**: Enforce a maximum platform fee cap of 10% (1,000 basis points) on-chain inside the smart contract validation logic and off-chain in the API / frontend forms.
* **Rationale**: Restricting custom platform fees to a maximum of 10% protects workers from potential fee-gouging schemes while providing creators with the flexibility needed to self-fund their operations.
* **Alternatives Considered**:
  * *No Cap (Unlimited)*: Allowing creators to set up to 100% platform fees. Rejected because it could lead to predatory bounty configurations that exploit worker labor with zero payout.
  * *Frontend-only Cap*: Enforcing the cap only in the React UI form. Rejected because malicious users can bypass the frontend and call the smart contract directly with custom configurations.

---

## 3. Frontend-only Disclaimer Validation & Checkboxes

* **Decision**: Implement mandatory checkbox components for the Peer-to-Peer Tax Liability and Agent Human Stewardship disclaimers in the wallet connection and bounty creation UI flow. State will be managed using local React state or localStorage, without any database persistence.
* **Rationale**: Purely frontend-only verification is sufficient to legally inform users and obtain acknowledgement before critical interactions (connecting wallet or posting a bounty). Avoiding backend persistence respects user privacy and avoids bloating the database with compliance logs.
* **Alternatives Considered**:
  * *Database Signature Logging*: Logging the user's wallet address and a timestamp of disclaimer acceptance in the backend database. Rejected because it is unnecessary for protocol-level de-risking and introduces additional DB maintenance.

---

## 4. Hosted Indexer Neutrality & Spam Filtering

* **Decision**: Remove filters checking for default treasury accounts in `gateway/indexer.py`. The crawler will process all application deployments that match the standard `escrow.algo` contract schema.
* **Rationale**: To prevent classification as a matching broker, the indexer must remain neutral and display all deployments of the open-source contract template, even if they set fees to 0% or redirect treasury funds.
* **Alternatives Considered**:
  * *Whitelist of Permitted Treasuries*: Maintaining an administrative whitelist of approved treasury targets. Rejected because it introduces gatekeeping and violates the hosted indexer neutrality principle (Constitution §5.6).
  * *No Filtering (All Transactions)*: Indexing any transaction. Rejected because we must filter out non-conforming application schemas to avoid spamming the database with unrelated applications.
