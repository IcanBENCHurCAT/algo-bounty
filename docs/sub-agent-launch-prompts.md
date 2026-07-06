# Sub-Agent Launch Prompts: AP2 & x402 Integration
This document contains 4 standalone, self-contained prompts to spawn sub-agents to build the respective parts of the AP2 / x402 / A2A integration plan.
---
## Sub-Agent 1: Cryptographic Validation & JCS Helper
* **Role**: Cryptographic Security Engineer
* **Scope**: Implement JCS (RFC 8785) formatting, ED25519 signature checks, and DID resolution caching.
* **Workspace**: FastAPI Backend (`gateway/`)
```text
Task: Implement the cryptographic verification layer for the A2A messaging router and DID verification.
Instructions:
1. Write a helper module `gateway/crypto.py` that implements:
   - JSON Canonicalization Scheme (JCS - RFC 8785) parsing. Given a JSON object/dict, format it deterministically (lexicographically sorted keys, compact spacing, escaped characters).
   - ED25519 signature validation. Implement a verify function using the `nacl` or `cryptography` Python package that takes a JCS-serialized byte string, a signature, and a public key.
2. Implement an asynchronous DID public key resolver with caching:
   - For a given DID like `did:web:agent.example.com`, fetch its DID Document at `https://agent.example.com/.well-known/did.json` to resolve the verification public key.
   - Cache the resolved public keys in memory or Redis with a 24-hour TTL to prevent DoS starvation on the gateway threads. Include a request timeout of 3 seconds.
3. Write comprehensive unit tests in `tests/test_crypto.py` covering canonicalization edge cases, invalid signatures, expired keys, and cache hit/miss flows.
```
---
## Sub-Agent 2: x402 Middleware & Replay Protection
* **Role**: Backend API Security Engineer
* **Scope**: FastAPI middleware for x402 parsing, scope checks, and Redis-based replay prevention.
* **Workspace**: FastAPI Backend (`gateway/`)
```text
Task: Implement the x402 Machine Pay HTTP headers parsing and security middleware in FastAPI.
Instructions:
1. Write a FastAPI middleware `gateway/middleware/x402.py` that intercepts requests to `/api/v2/bounties/{id}/accept` and related endpoints containing x402 headers.
2. The middleware must parse:
   - `x-402-amount`, `x-402-currency`, `x-402-scope`, `x-402-timestamp`, `x-402-nonce`, and `x-402-signature`.
3. Implement the following verification checks:
   - Replay Protection: Assert that `x-402-timestamp` is within a 300-second window of the current system time.
   - Nonce Uniqueness: Query and store the `x-402-nonce` in Redis using a 300-second TTL. If the key already exists, reject with HTTP 401.
   - Signature Verification: Re-assemble the canonical JCS signature payload from the headers and verify the signature using the sender's public key (retrieved from the Agent Registry).
4. Implement Scope Mapping:
   - Map `x-402-scope: escrow-release:{bounty_id}` to verify that the bounty's state is SUBMITTED before routing the request.
5. Write unit tests in `tests/test_x402_middleware.py` verifying request expiration, nonce collisions, invalid signatures, and unauthorized scopes.
```
---
## Sub-Agent 3: Smart Contract Mediator & Bonding Logic
* **Role**: Smart Contract (AVM) Developer
* **Scope**: Extend `escrow.py` with mediator bonding logic and box consolidation.
* **Workspace**: Smart Contract (`escrow.py` / `escrow.teal`)
```text
Task: Update the smart contract escrow logic to support mediator fee allocation and mediator bonding without exceeding AVM box constraints.
Instructions:
1. Open `escrow.py` and inspect the box layouts.
2. Extend the contract states and box models to support:
   - Storing a mediator fee allocation (e.g. 0.25% of the bounty payout).
   - Storing a binary representation of the mediator's bonded status.
3. Box Limit Hardening:
   - Because AVM is limited to 8 box references per transaction, pack the mediator's DID hash, address, and bond amount into a single box (e.g., `mediator_bond` box) using binary packing instead of using separate boxes for each attribute.
4. Implement on-chain fee splitting during payout:
   - If a dispute is settled by a mediator, the payout logic should execute:
     - 2% to platform treasury.
     - 0.25% to mediator account.
     - Remainder to the worker (or refunded to creator depending on the verdict).
5. Compile both the testnet and mainnet contract versions to update the compiled approval/clear programs.
```
---
## Sub-Agent 4: Federated Mediation Routing Engine
* **Role**: Database & Systems Orchestrator
* **Scope**: Implement mediator registry APIs, selection algorithm, and dispute lifecycle states.
* **Workspace**: Database Schema & API Routing (`gateway/`)
```text
Task: Implement the API endpoints, database models, and selection logic for the Federated Mediation system.
Instructions:
1. Define the PostgreSQL database models for:
   - `mediators`: Stores the registry of mediator profiles, specializations, max concurrent disputes, and min required Karma.
   - `dispute_assignments`: Stores assignments connecting disputes to mediators, tracking verdict statuses and rationale logs.
2. Write the API endpoints in `gateway/routers/mediators.py`:
   - `POST /api/v2/mediators/register`: Registers/updates mediator agent profiles.
   - `POST /api/v2/mediations/decide`: Allows an assigned mediator to submit a verdict.
   - `POST /api/v2/mediations/appeal`: Allows posters/hunters to appeal a mediator's decision.
3. Write the mediator selection algorithm:
   - When a dispute is filed, filter mediators by:
     - Match specialization tags (e.g., "smart-contracts" or "python").
     - Highest Karma score.
     - Lowest concurrent active disputes (under max concurrent limit).
   - Assign the dispute to the selected mediator and send an A2A notification message.
4. Integrate with the backend approve/payout logic to execute the appropriate smart contract payouts based on the mediator's verdict.
```
