# Implementation Tasks: Pre-Mainnet Launch Preparation & Final Hardening

**Branch**: `003-premainnet-launch-prep` | **Spec**: [specs/003-premainnet-launch-prep/spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/003-premainnet-launch-prep/spec.md) | **Plan**: [specs/003-premainnet-launch-prep/plan.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/003-premainnet-launch-prep/plan.md)

---

## Phase 1: Setup & Environment Prep

- [X] T001 Verify git status on branch `003-premainnet-launch-prep` and ensure workspace clean.
- [X] T002 Verify Python virtual environment active and `pytest` dependencies available.
- [X] T003 Verify `dashboard/` npm dependencies available and `npx tsc --noEmit` runs clean.

---

## Phase 2: Smart Contract Layer — Fee Parameterization & 30-Day Timeout (`escrow.py`)

- [X] T004 [US1] Update `EscrowContract.__init__()` in `escrow.py` to declare `self.platform_fee = Box(UInt64, key="platform_fee")`.
- [X] T005 [US1] Update `create_bounty()` in `escrow.py` to accept `platform_fee: UInt64`, validate $1 \le \text{platform\_fee} \le 1000$ (max 10.0%), and set box storage value.
- [X] T006 [US1] Update `_get_platform_fee()` helper in `escrow.py` to read `platform_fee` box with fallback to 200 bps (2.0%).
- [X] T007 [US1] Update `_send_payout_with_royalties()` in `escrow.py` to use `self._get_platform_fee()` for fee calculation.
- [X] T008 [US1] Ensure `self.platform_fee.delete()` is executed upon bounty closure in `approve_work()`, `claim_abandoned()`, and `resolve_dispute()`.
- [X] T009 [US4] Define `DISPUTE_TIMEOUT = UInt64(2592000)` (30 days in seconds) in `escrow.py`.
- [X] T010 [US4] Add `@arc4.abimethod` `resolve_dispute_timeout(self)` in `escrow.py` enforcing `state == DISPUTED`, `Global.latest_timestamp > dispute_timestamp + DISPUTE_TIMEOUT`, and executing 50/50 split resolution (`SPLIT`).
- [X] T011 [US1,US4] Recompile TEAL contract artifacts via `python compile_teal.py` and verify zero compilation errors.
- [X] T012 [US1,US4] Update `tests/test_fee_split.py` and `tests/test_admin_disputes.py` to test parameterized platform fee rates and 30-day dispute timeout execution.
- [X] T013 [US1,US4] Run `PYTHONPATH=. python -m pytest tests/test_fee_split.py tests/test_admin_disputes.py -v` and ensure all tests pass.

---

## Phase 3: Backend Gateway Updates (`gateway/`)

- [X] T014 [US1] Update `BountyCreate` schema in `gateway/schemas.py` to include optional `platform_fee: Optional[int] = 200`.
- [X] T015 [US1] Update `gateway/routers/bounties.py` creation endpoint to pass `platform_fee` to contract invocation.
- [X] T016 [US2] Update `gateway/routers/admin.py` to ensure `GET /api/v1/admin/quarantines`, `POST /api/v1/admin/quarantines/{id}/resolve`, and `POST /api/v1/admin/disputes/{id}/resolve` return consistent, structured responses.

---

## Phase 4: Frontend API & Navigation (`dashboard/`)

- [X] T017 [US2] Update `dashboard/src/lib/api.ts` to add API methods: `getQuarantines()`, `resolveQuarantine()`, and `adminResolveDispute()`.
- [X] T018 [US2] Update `dashboard/src/components/DashboardLayout.tsx` to display conditional "Admin Portal" link in sidebar when `connectedAddress === ADMIN_ADDRESS`.

---

## Phase 5: Admin Management Portal (`dashboard/src/app/admin/page.tsx`)

- [X] T019 [US2] Create `/admin` page component `dashboard/src/app/admin/page.tsx` with `'use client'` directive.
- [X] T020 [US2] Implement Admin Authorization Check on `/admin`: Display 403 Forbidden banner if connected wallet does not match `ADMIN_ADDRESS`.
- [X] T021 [US2] Implement "Disputed Bounties" tab on `/admin` displaying active disputed bounties, GitHub PR links, escrow amounts, and 1-click resolution buttons (`Worker Win`, `Creator Win`, `Split`).
- [X] T022 [US2] Implement "Account Quarantines" tab on `/admin` displaying active/resolved quarantine records, reasons, details, and 1-click resolution buttons (`Clear Quarantine`, `Penalize`).
- [X] T023 [US2] Add visual toast notifications and state refetch upon resolving disputes or clearing quarantines.

---

## Phase 6: Terms of Service Modal (`dashboard/src/components/TermsModal.tsx`)

- [X] T024 [US3] Create `dashboard/src/components/TermsModal.tsx` displaying non-custodial software disclaimers, FAA arbitration clauses, and Phase 1 best-effort admin stewardship rules.
- [X] T025 [US3] Integrate `TermsModal` into `dashboard/src/components/AuthProvider.tsx` or `DashboardLayout.tsx` on wallet connect.
- [X] T026 [US3] Persist acceptance in `localStorage` under `algobounty_tos_accepted`.

---

## Phase 7: Verification & E2E Validation

- [X] T027 Run full pytest test suite: `PYTHONPATH=. python -m pytest tests/ -v`.
- [X] T028 Check TypeScript compilation in `dashboard/`: `cd dashboard && npx tsc --noEmit`.
- [X] T029 Verify quickstart validation scenarios in `specs/003-premainnet-launch-prep/quickstart.md`.
