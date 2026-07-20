# Data Model Updates

## Database Entity: `bounties` (or related state)
- **New Field**: `authorized_app_id` (Integer / String) - Stores the GitHub App ID or Installation ID of the community node that created the bounty.
- **New Field**: `hitm_enforced` (Boolean) - True if the bounty lacks a verified app identity and must be manually approved.

## Smart Contract State: `Escrow`
- **New Box/State**: `authorized_app_id` or similar flag to track if the bounty is tied to a trusted app, OR if it strictly requires HITM (Human-In-The-Middle) approval.
