# ADR 0010: Direct-to-Chain Fallback

**Date**: 2026-07-20
**Status**: Implemented

## Context
In alignment with the sovereign frontend requirements (Constitution §5.11), the dashboard must minimize reliance on a centralized backend. If the Gateway API is offline or unreachable, the frontend must remain usable for viewing data.

## Decision
1. **Unreachability Detection**: Implement a custom react hook `useFallbackMode` that tracks when the Gateway API is offline (catching connection errors or 5xx responses).
2. **Blockchain Bypass**: When fallback mode is active, the frontend routes data queries directly to public Algorand indexers (e.g. AlgoNode) using `algosdk` in a dedicated indexer fallback service (`dashboard/src/services/indexerFallback.ts`).
3. **Read-Only Lock**: When operating in fallback mode, state-mutating actions (like creating or claiming bounties) are disabled across all dashboard components, and a persistent visual banner notifies the user of the read-only fallback state.

## Consequences
* **Positive**: Increases platform availability and decentralized portability, allowing users to view bounty details and proof statements directly from the blockchain even during total gateway API outages.
* **Negative**: Fallback mode does not support complex database-driven search, filtering, or write operations, which are locked to avoid inconsistency.
