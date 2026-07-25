# Research: Phase 1 Pre-Mainnet Hardening

**Date**: 2026-07-25
**Feature**: [spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/002-phase1-hardening/spec.md)

## R-001: State Machine Post-MAX_REJECTIONS Behavior

**Decision**: After `MAX_REJECTIONS` (3) is reached, the contract's `reject_work()` method already prevents further rejections (`assert rejection_count < MAX_REJECTIONS`). Currently, `claim_abandoned()` allows the **creator** to call a refund from `REJECTED` state when `rejection_count >= MAX_REJECTIONS`. The spec demands this transitions to `DISPUTED` instead — but research shows the creator is the one calling `claim_abandoned()`, not the system auto-transitioning.

**Rationale**: The current `claim_abandoned()` method is the griefing vector: a creator grief-rejects 3 times, then calls `claim_abandoned()` to get a refund and keep the code. The fix must:
1. Remove or restructure `claim_abandoned()` so it cannot be called when `REJECTED` state was reached due to creator rejections of valid work.
2. Add a new `escalate_to_dispute()` method callable by the **worker** from `REJECTED` state when `rejection_count >= MAX_REJECTIONS`, which transitions to `DISPUTED`.
3. Keep `claim_abandoned()` available only after a timeout period where the worker has not re-submitted or escalated.

**Alternatives considered**:
- Auto-transitioning to `DISPUTED` on the 3rd rejection call itself — Rejected because it removes the creator's ability to legitimately end a failed engagement.
- Removing `claim_abandoned()` entirely — Rejected because creators need a way to recover funds from genuinely abandoned bounties (worker disappeared after rejection).

---

## R-002: Refund Lock from SUBMITTED State

**Decision**: There is **no standalone `refund_bounty()` method** in the escrow contract. Refunds are only possible via:
1. `claim_abandoned()` — requires `REJECTED` state + `rejection_count >= MAX_REJECTIONS`
2. `auto_resolve_creator_win()` — requires `DISPUTED` state + 14-day timeout
3. Arbitration vote option 2 (creator_win) — requires `DISPUTED` state
4. `resolve_dispute()` with "creator_win" — requires `DISPUTED` state + valid mediator signature

**Rationale**: The on-chain contract **already** prevents refunds from `SUBMITTED` state because none of the refund paths accept `SUBMITTED` as a precondition. The spec requirement (FR-002) is already met on-chain. The risk is purely at the **gateway/off-chain** layer — if the backend ever adds a "refund" API endpoint that bypasses the contract, it would break this invariant. The fix is documentation + gateway-level assertion.

**Alternatives considered**:
- Adding an explicit `assert self.state_box.value != SUBMITTED` to a new method — unnecessary since no refund method accepts SUBMITTED.

---

## R-003: Manual GitHub Sync Architecture

**Decision**: Implement a `POST /api/v1/bounties/{bounty_id}/sync-github` endpoint that:
1. Reads the bounty's linked GitHub issue/PR state via the GitHub API.
2. If the PR is merged or issue is closed and the bounty is in `submitted` state, updates the DB status to `ready_for_payout`.
3. Returns the updated status to the caller, but does NOT trigger `release_trustless()`.
4. A separate `POST /api/v1/bounties/{bounty_id}/claim-payout` endpoint allows the **worker** (authenticated via JWT) to authorize the actual fund release.

**Rationale**: The current architecture uses `release_trustless()` in `gateway/github.py`, which is called by the backend using `PLATFORM_PRIVATE_KEY` to sign `approve_work()` on the contract. This is a push model. The pull model requires the worker to sign the transaction themselves. However, the contract's `approve_work()` currently checks `Txn.sender == creator OR Txn.sender == gateway`. To support worker-initiated pull, we need to either:
- Add the worker as an authorized caller in `approve_work()` when the state is `ready_for_payout` (requires contract change), OR
- Keep the backend as the signer but require the worker to explicitly trigger it (hybrid pull — worker initiates, backend executes).

For Phase 1, the **hybrid pull** approach is recommended: the worker clicks "Claim Payout," the backend verifies GitHub state, and only then calls `release_trustless()`. This avoids a contract change while achieving the spec's intent.

**Alternatives considered**:
- Pure worker-signed pull (worker signs `approve_work()`) — Rejected for Phase 1 because it requires a contract upgrade. Planned for Phase 2.
- Keeper/relayer incentive (Dr. Nash's proposal) — Deferred to Phase 2 as it requires a fee mechanism.

---

## R-004: Evaluator Rename Scope

**Decision**: Rename "arbitrator" → "evaluator" across all layers:

| Layer | Files | Scope |
|-------|-------|-------|
| **Smart Contract** | `escrow.py` | Log strings (`arbitrator_registered`, `arbitrator_deregistered`, `arbitrator_voted`), method names (`register_arbitrator`, `deregister_arbitrator`), box key prefixes (`cand_addr_`, `cand_idx_`), state box names (`arbitrator_1`, `arbitrator_2`, `arbitrator_3`, `arbitrator_1_vote`, etc.) |
| **Gateway Schemas** | `gateway/schemas.py` | 5 schema classes: `ArbitratorRegistrationResponse`, `ArbitratorResponse`, `ArbitratorListResponse`, `ArbitratorMeResponse`, `ArbitratorVoteResponse` |
| **Gateway Router** | `gateway/routers/arbitrators.py` | File rename → `evaluators.py`, route prefix `/api/v1/arbitrators` → `/api/v1/evaluators` |
| **DB Models** | `gateway/supabase_migration.py` | Table names: `arbitrators` → `evaluators`, `dispute_arbitrators` → `dispute_evaluators`. Column: `arbitrator_address` → `evaluator_address` |
| **Worker** | `gateway/worker.py` | Log parsing for `arbitrator_voted`, `dispute_submitted` (arbitrator address decoding), `arbitrator_registered`, `arbitrator_deregistered` |
| **Frontend** | `dashboard/src/lib/api.ts`, `dashboard/src/app/mediators/page.tsx` | API type names and endpoint paths |
| **Tests** | `tests/test_arbitrators.py` | File rename → `test_evaluators.py`, all assertion references |

**Rationale**: The rename must be comprehensive to satisfy SC-004 ("zero instances of 'arbitrator'"). The smart contract rename is the most impactful because it changes ABI method selectors, requiring any existing deployed contracts to be redeployed. This is acceptable because we are pre-mainnet.

**Alternatives considered**:
- Partial rename (UI only, keep backend/contract) — Rejected because inconsistency creates maintenance burden and doesn't fully address the legal risk.
- "Reviewer" instead of "evaluator" — Both are acceptable; "evaluator" chosen because it implies expertise/assessment rather than code review (which might conflict with GitHub's "reviewer" concept).

---

## R-005: Admin-Gated Dispute Resolution

**Decision**: Add a new `gateway/routers/admin.py` router with:
1. `POST /api/v1/admin/disputes/{bounty_id}/resolve` — Admin-only endpoint accepting `{resolution: "worker_win" | "creator_win" | "split"}`.
2. The endpoint calls the appropriate contract method (`resolve_dispute` with the platform's mediator signature, or the existing arbitration payout methods).
3. Gated behind a new `is_admin` check on the JWT (the platform admin's wallet address).

**Rationale**: During Phase 1, the 3-evaluator panel is premature (per Maya's analysis and the spec). Admin resolution provides a reliable fallback while the user base grows. The existing `resolve_dispute()` contract method accepts a mediator signature — the admin can use the platform's mediator key to sign resolutions.

**Alternatives considered**:
- Reusing the existing `resolve_dispute()` method with the platform mediator key — This is exactly what we'll do. No new contract method needed.

---

## R-006: Quarantine System

**Decision**: Add a new `AccountQuarantine` model to the database with fields: `address`, `reason`, `quarantined_at`, `expires_at`, `resolved_by`, `resolved_at`, `resolution` (cleared/penalized). Add middleware in the bounty creation endpoint to check quarantine status before allowing new bounties.

**Rationale**: Quarantine is a purely off-chain mechanism (the smart contract doesn't need to know about it). The gateway enforces it by rejecting `POST /api/v1/bounties` requests from quarantined addresses. This is simpler and more appropriate than on-chain enforcement for Phase 1.

**Alternatives considered**:
- On-chain quarantine flag in contract boxes — Over-engineered for Phase 1 and adds MBR costs.
- Banning (permanent) instead of quarantine (temporary) — Rejected because false positives are likely, and permanent bans destroy trust.

---

## R-007: Contract Upgrade Strategy

**Decision**: The smart contract changes (state machine hardening + evaluator rename) require a new contract deployment. Since we are pre-mainnet and each bounty is a separate application deployment, existing bounties continue to use the old contract, and new bounties use the updated contract.

**Rationale**: Algorand application contracts are immutable once deployed. The AlgoBounty architecture deploys a fresh contract instance per bounty, so there is no global "upgrade" — new bounties simply use the new compiled TEAL.

**Alternatives considered**:
- In-place upgrade via `UpdateApplication` — Not supported by the current contract design (`delete_bounty` uses `DeleteApplication` but no `UpdateApplication` handler exists).
