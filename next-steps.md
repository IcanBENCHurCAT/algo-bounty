# Next Steps for AlgoBounty

The following features and improvements are planned for the next phase of development:

## 1. High Priority: Smart Contract & HITM Mode [COMPLETE]
- [x] **Full HITM Flow Testing**: Verified the Human-in-the-Middle review window and auto-release logic via `indexer_polling_task` log processing.
- [x] **Dispute Resolution Refinement**: Corrected timeout constants in `escrow.algo` and implemented on-chain split logic handling in the gateway.
- [x] **Karma System Integration**: Implemented full karma scoring rules (v2) in both the router lifecycle and background indexer sync.

## 2. GitHub Integration Enhancements
- **OIDC Bridge**: Implement the full GitHub OIDC token verification for automated bounty payouts (trustless mode).
- **GitHub App Permissions**: Refine the permissions required for the GitHub App to ensure minimal access while still being able to post comments and link PRs.
- **PR Linking Logic**: Improve the robustness of linking PRs to bounties, handling cases where multiple PRs might refer to the same bounty.

## 3. Frontend Improvements
- **Real-time Status Updates**: Enhance the dashboard to show real-time on-chain status for bounties using the indexer's sync data.
- **Wallet Support**: Expand beyond Pera Wallet to support other Algorand wallets like Defly and Edge.
- **Bounty Creation UX**: Improve the UI for creating bounties, including better validation and feedback for on-chain deployment.

## 4. Indexer & Backend Robustness
- **Indexer Polling Refinement**: Move the background polling task to a dedicated asynchronous service (e.g., using Celery or a standalone worker process) to improve scalability and isolation from the main API.
- **Bulk Transaction Search**: Optimize the `indexer_polling_task` to use a single `search_transactions` call for all relevant app IDs instead of polling each app individually.
- **Active Cleanup Triggering**: Implement logic for the Gateway to actively call on-chain cleanup methods (`expire_claim`, `auto_release`, `timeout_dispute`) when internal deadlines are met, rather than just reacting to logs.
- **Database Migrations**: Continue using Alembic for all schema changes.
- **Secret Management**: Move sensitive environment variables (e.g., `GITHUB_TOKEN`, `PLATFORM_PRIVATE_KEY`) to a secure secret manager in production.

## 5. Testing & Documentation
- **Target 80% Coverage**: Expand the unit and integration test suites to cover all edge cases in the bounty lifecycle.
- **API Documentation**: Maintain the FastAPI Swagger UI and ensure all new endpoints are well-documented.
- **Developer Guide**: Update `CONTRIBUTING.md` with instructions on how to set up a local development environment with the new background tasks.
