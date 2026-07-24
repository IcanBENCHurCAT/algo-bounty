# ADR 0003: Indexer Neutrality & Compliance

**Date**: 2026-07-19

**Status**: Accepted

## Context
As a decentralized marketplace, AlgoBounty must avoid being classified as a commercial matching broker or centralized custodian. According to Constitution §§5.6-5.8 (Spec 009), the hosted indexer cannot filter or censor bounties based on their fee structure or treasury destinations. Furthermore, the platform must ensure that users (creators, workers, and autonomous agents) are explicitly aware of their peer-to-peer tax liabilities and the requirement for human stewardship of agent accounts.

## Decision
1. **Hosted Indexer Neutrality**: The backend indexer (`gateway/indexer.py`) will be modified to remove all filtering based on treasury addresses or fee percentages. It will neutrally index and display all deployments that match the standard contract schema. Basic spam/security filtering of malformed contracts is permitted.
2. **Custom Fee Overrides**: 
   - Creators will be allowed to override the default platform fee percentage (capped at a maximum of 10%) and specify custom treasury destination addresses during bounty creation. 
   - The database schema (SQLAlchemy/Supabase) will be updated to store and serve these custom parameters per bounty.
3. **Mandatory Compliance Disclaimers**: The frontend UI will introduce mandatory checkboxes for "P2P Tax Liability" and "Agent Human-Stewardship". 
   - Users cannot connect their wallets or create bounties without explicitly acknowledging these disclaimers. 
   - These checks will be validated entirely on the frontend and will not be stored in the database or on-chain.

## Consequences
- **Positive**: Protects the platform from regulatory scrutiny by clearly establishing the backend as a neutral, non-commercial indexer rather than a proprietary broker. Educates users on their legal responsibilities in a peer-to-peer network.
- **Negative**: Custom fee logic introduces variability that could confuse users; the 10% cap must be rigidly enforced in both the UI and contract to prevent abuse. Mandatory checkboxes add slight friction to the onboarding and creation UX.
