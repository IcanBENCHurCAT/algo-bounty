# Research & Decisions

## Decision: App Authentication
- **Decision**: Use `jwt` generation with GitHub App Private Key to authenticate as the app installation.
- **Rationale**: Replaces legacy PATs and satisfies BYOA requirements, preventing central rate limit bottlenecks.
- **Alternatives considered**: OAuth apps (requires user interaction, unsuitable for autonomous gateway).

## Decision: Bounty Authorized App Tracking
- **Decision**: Store `authorized_app_id` in the Bounty escrow contract state or database when created, and enforce that only webhooks matching that installation can auto-approve, otherwise fall back to HITM mode.
- **Rationale**: Ensures untrusted community nodes cannot forge webhook events to auto-approve bounties they didn't create.
- **Alternatives considered**: Rely entirely on OIDC. OIDC not fully supported on-chain yet, so App ID tracking + HITM fallback is chosen per spec.
