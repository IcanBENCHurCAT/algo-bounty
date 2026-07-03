# Next Steps for AlgoBounty

The following features and improvements are planned for the next phase of development:

## 1. High Priority: Smart Contract & HITM Mode
- **Full HITM Flow Testing**: Verify the Human-in-the-Middle review window (default 7 days) and auto-release logic.
- **Dispute Resolution Refinement**: Implement the 30-day dispute timeout with 50/50 split as defined in the `escrow.algo` contract.
- **Karma System Integration**: Ensure all on-chain events (claim, submit, approve, ghosting) correctly trigger karma updates in the database.

## 2. GitHub Integration Enhancements [COMPLETED]
- [x] **OIDC Bridge**: Implement the full GitHub OIDC token verification for automated bounty payouts (trustless mode).
- [x] **GitHub App Permissions**: Refine the permissions required for the GitHub App to ensure minimal access while still being able to post comments and link PRs.
- [x] **PR Linking Logic**: Improve the robustness of linking PRs to bounties, handling cases where multiple PRs might refer to the same bounty.

## 3. Frontend Improvements
- **Real-time Status Updates**: Enhance the dashboard to show real-time on-chain status for bounties using the indexer's sync data.
- **Wallet Support**: Expand beyond Pera Wallet to support other Algorand wallets like Defly and Edge.
- **Bounty Creation UX**: Improve the UI for creating bounties, including better validation and feedback for on-chain deployment.

## 4. Indexer & Backend Robustness (COMPLETED)
- **Indexer Polling Refinement**: [DONE] Moved to standalone worker `gateway/worker.py`.
- **Database Migrations**: [DONE] Standardized on Alembic for all schema changes with `gateway/alembic.ini`.
- **Secret Management**: [DONE] Centralized in `gateway/config.py` with extensible secret manager support.

## 5. Testing & Documentation
- **Target 80% Coverage**: Expand the unit and integration test suites to cover all edge cases in the bounty lifecycle.
- **API Documentation**: Maintain the FastAPI Swagger UI and ensure all new endpoints are well-documented.
- **Developer Guide**: Update `CONTRIBUTING.md` with instructions on how to set up a local development environment with the new background tasks.
