# Phase 0: Research

## Unknowns Resolved

### 1. Which public Algorand indexer endpoints to use?
- **Decision**: Use AlgoNode public indexer APIs (e.g., `https://testnet-idx.algonode.cloud` for testnet, `https://mainnet-idx.algonode.cloud` for mainnet).
- **Rationale**: Free, publicly accessible, and commonly used by the Algorand community for decentralized frontends.
- **Alternatives considered**: Running a dedicated indexer (violates BYOA and sovereign frontend principles for this specific fallback use case).

### 2. How to detect Gateway API unreachability in React?
- **Decision**: Implement a fallback strategy in the data fetching layer. If the API returns a 5xx error or fails to fetch (e.g., connection refused), catch the error, set an `isFallbackMode` state, and immediately execute a secondary fetch against the public indexer.
- **Rationale**: Clean, centralized handling of network errors without polluting every component.
- **Alternatives considered**: Pinging the backend health endpoint periodically (adds unnecessary overhead).

### 3. What schema does the public indexer return, and how to map it?
- **Decision**: Use the `/v2/applications/{app-id}/boxes` and related endpoints or fetch via `algosdk`. The data will need to be decoded in the frontend using `algosdk` utility functions to match the basic `Bounty` listing schema (id, amount, status).
- **Rationale**: Directly aligns with on-chain data representation.
