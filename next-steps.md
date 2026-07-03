# Next Steps for AlgoBounty

The following features and improvements are planned for the next phase of development:

## 1. High Priority: Smart Contract & HITM Mode
- **Full HITM Flow Testing**: Verify the Human-in-the-Middle review window (default 7 days) and auto-release logic.
- **Dispute Resolution Refinement**: Implement the 30-day dispute timeout with 50/50 split as defined in the `escrow.algo` contract.
- **Karma System Integration**: Ensure all on-chain events (claim, submit, approve, ghosting) correctly trigger karma updates in the database.

## 2. GitHub Integration Enhancements
- **OIDC Bridge**: Implement the full GitHub OIDC token verification for automated bounty payouts (trustless mode).
- **GitHub App Permissions**: Refine the permissions required for the GitHub App to ensure minimal access while still being able to post comments and link PRs.
- **PR Linking Logic**: Improve the robustness of linking PRs to bounties, handling cases where multiple PRs might refer to the same bounty.

## 3. Frontend Improvements [COMPLETED]
- **Real-time Status Updates**: Implemented via `useEvents` hook subscribing to `/api/v1/events` SSE. Dashboard now refreshes automatically on bounty events.
- **Wallet Support**: Expanded `useWallet` to support Defly and Edge wallets. Added a wallet selection menu to `WalletConnect`.
- **Bounty Creation UX**: Created a dedicated multi-step bounty creation page (`/create`) with validation and deployment status feedback.

## 4. Indexer & Backend Robustness
- **Indexer Polling Refinement**: Move the background polling task to a dedicated asynchronous service (e.g., using Celery or a standalone worker process) to improve scalability and isolation from the main API.
- **Database Migrations**: Continue using Alembic for all schema changes.
- **Secret Management**: Move sensitive environment variables (e.g., `GITHUB_TOKEN`, `PLATFORM_PRIVATE_KEY`) to a secure secret manager in production.

## 5. Testing & Documentation
- **Target 80% Coverage**: Expand the unit and integration test suites to cover all edge cases in the bounty lifecycle.
- **API Documentation**: Maintain the FastAPI Swagger UI and ensure all new endpoints are well-documented.
- **Developer Guide**: Update `CONTRIBUTING.md` with instructions on how to set up a local development environment with the new background tasks.
