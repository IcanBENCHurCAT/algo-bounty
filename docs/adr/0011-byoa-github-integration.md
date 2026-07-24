# v11: BYOA GitHub Integration with Delegated Trust

This document details the architectural decisions made during the implementation of the BYOA GitHub Integration feature.

---

## Status
Approved / Implemented

## Context & Problem
AlgoBounty is transitioning to a Bring Your Own App (BYOA) model to decentralize infrastructure and remove reliance on a centralized GitHub App for issue tracking and webhook processing. Community nodes need to securely authenticate as their own GitHub Apps and trigger escrow actions securely on-chain.

## Decision
1. **GitHub App Authentication**: The backend gateway securely stores `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`, and `GITHUB_INSTALLATION_ID` to generate JSON Web Tokens (JWT) for authenticating GitHub API calls instead of using personal access tokens.
2. **On-Chain Delegated Trust**: The smart contract tracks the `authorized_app_id` (a `UInt64`) per-bounty to ensure only the app designated at creation can auto-approve the bounty.
3. **HITM Mode Enforcement**: If an authorized app is not supplied (e.g. `authorized_app_id == 0`), the smart contract enforces Human-In-The-Middle (HITM) mode automatically.
4. **Secure Webhook Binding**: The gateway validates all incoming GitHub webhooks using HMAC-SHA256 signatures derived from the GitHub App's secret key.

## Consequences
**Positive**:
- Removes centralized vendor lock-in for community-hosted nodes.
- High security for automated escrow releases through cryptographically verified GitHub webhooks and on-chain identity tracking.
- Fallback to HITM mode ensures bounties can't be stolen automatically via spoofing if an app isn't configured.

**Negative**:
- Adds slight complexity to node operation (operators must register their own GitHub App and supply credentials).

## Superseded Decisions
- **0005-github-integration**: The previous GitHub integration architecture relied on personal access tokens and a more centralized model, which is superseded by this decentralized BYOA approach.
