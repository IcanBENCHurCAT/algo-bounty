# Phase 1: Quickstart Validation Guide

## Scenarios to Validate

### Scenario 1: Trigger Fallback Mode
1. **Prerequisites**: Ensure the frontend development server is running (`npm run dev` in `dashboard`).
2. **Setup**: Stop the backend Gateway API server.
3. **Run**: Navigate to `http://localhost:3001/dashboard`.
4. **Expected Outcome**: The dashboard loads successfully. A visible banner indicates "Read-Only / Fallback Mode". Bounties are displayed using data fetched directly from the public Algorand indexer.

### Scenario 2: Action Disablement
1. **Prerequisites**: Frontend running in fallback mode (Gateway API is offline).
2. **Run**: Attempt to click "Create Bounty" or "Claim" on an existing bounty.
3. **Expected Outcome**: The buttons are disabled or show a warning tooltip explaining that state-mutating actions require the Gateway API.
