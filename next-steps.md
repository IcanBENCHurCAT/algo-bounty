# Next Steps for AlgoBounty

The following features and improvements are planned for the next phase of development:

## 1. High Priority: Smart Contract & HITM Mode [COMPLETE]
- [x] **Full HITM Flow Testing**: Verified the Human-in-the-Middle review window and auto-release logic via `indexer_polling_task` log processing.
- [x] **Dispute Resolution Refinement**: Corrected timeout constants in `escrow.algo` and implemented on-chain split logic handling in the gateway.
- [x] **Karma System Integration**: Implemented full karma scoring rules (v2) in both the router lifecycle and background indexer sync.

## 2. GitHub Integration Enhancements [COMPLETED]
- [x] **OIDC Bridge**: Implement the full GitHub OIDC token verification for automated bounty payouts (trustless mode).
- [x] **GitHub App Permissions**: Refine the permissions required for the GitHub App to ensure minimal access while still being able to post comments and link PRs.
- [x] **PR Linking Logic**: Improve the robustness of linking PRs to bounties, handling cases where multiple PRs might refer to the same bounty.

## 3. Frontend Improvements [COMPLETED]
- **Real-time Status Updates**: Implemented via `useEvents` hook subscribing to `/api/v1/events` SSE. Dashboard now refreshes automatically on bounty events.
- **Wallet Support**: Expanded `useWallet` to support Defly and Edge wallets. Added a wallet selection menu to `WalletConnect`.
- **Bounty Creation UX**: Created a dedicated multi-step bounty creation page (`/create`) with validation and deployment status feedback.

## 4. Indexer & Backend Robustness [COMPLETED]
- [x] **Indexer Polling Refinement**: Moved to standalone worker `gateway/worker.py`.
- [x] **Database Migrations**: Standardized on Alembic for all schema changes with `gateway/alembic.ini`.
- [x] **Secret Management**: Centralized in `gateway/config.py` with extensible secret manager support.
- [ ] **Bulk Transaction Search**: (Planned) Optimize the `indexer_polling_task` to use a single `search_transactions` call for all relevant app IDs instead of polling each app individually.
- [ ] **Active Cleanup Triggering**: (Planned) Implement logic for the Gateway to actively call on-chain cleanup methods (`expire_claim`, `auto_release`, `timeout_dispute`) when internal deadlines are met, rather than just reacting to logs.

## 5. Testing & Documentation
- **Target 80% Coverage**: Expand the unit and integration test suites to cover all edge cases in the bounty lifecycle.
- **API Documentation**: Maintain the FastAPI Swagger UI and ensure all new endpoints are well-documented.
- **Developer Guide**: Update `CONTRIBUTING.md` with instructions on how to set up a local development environment with the new background tasks.
