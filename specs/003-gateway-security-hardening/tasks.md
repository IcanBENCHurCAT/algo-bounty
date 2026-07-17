# Tasks: Gateway Security Hardening

**Input**: Design documents from `/specs/003-gateway-security-hardening/`

**Prerequisites**: plan.md (loaded), spec.md (loaded), research.md (loaded), data-model.md (loaded), contracts/ (loaded)

**Tests**: Test updates are required — existing test `test_rate_limiter.py` explicitly tests the vulnerable behavior and must be updated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project structure needed — all changes are modifications to existing files. This phase verifies the pre-conditions.

- [ ] T001 Verify `gateway/auth.py` exports `verify_jwt_token` and confirm its signature accepts a raw token string in `gateway/auth.py`
- [ ] T002 Verify existing test suite passes before any changes by running `python -m pytest tests/ -v`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational/blocking work is needed. All three user stories modify independent files and can proceed directly.

**⚠️ CRITICAL**: Phase 1 verification must complete before proceeding.

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Rate Limit Enforcement Against Forged Tokens (Priority: P1) 🎯 MVP

**Goal**: Replace the regex-only JWT format check in the rate limiter middleware with cryptographic JWT verification, so forged tokens no longer bypass rate limiting.

**Independent Test**: Send requests with fake `Bearer aaa.bbb.ccc` headers and verify they are rate-limited. Send requests with real JWTs and verify they still bypass rate limiting.

### Implementation for User Story 1

- [ ] T003 [US1] Import `verify_jwt_token` from `gateway.auth` and replace the regex-based JWT check (lines 153-159) with a `try/except Exception` block that calls `verify_jwt_token(token_part)` — if it returns a truthy value, bypass rate limiting; if it raises any exception (including `HTTPException`), fall through to IP-based rate limiting in `gateway/rate_limiter.py`
- [ ] T004 [US1] Update `test_rate_limiter_middleware_bypass` to expect that `Bearer aaa.bbb.ccc` is now rate-limited (invert assertion on line 75-76 from `status_code == 200` to `status_code == 429`) in `tests/test_rate_limiter.py`
- [ ] T005 [US1] Add new test `test_rate_limiter_valid_jwt_bypass` that generates a real JWT via `gateway.auth.create_jwt_token("TEST_ADDR")`, sends it as `Authorization: Bearer <token>`, and asserts the request bypasses rate limiting (returns 200 even when the IP-based limit is exhausted) in `tests/test_rate_limiter.py`
- [ ] T006 [US1] Add new test `test_rate_limiter_expired_jwt_no_bypass` that generates an expired JWT (mock `time.time` or set `exp` in the past), sends it as a Bearer token, and asserts the request is rate-limited in `tests/test_rate_limiter.py`
- [ ] T007 [US1] Run `python -m pytest tests/test_rate_limiter.py -v` and verify all rate limiter tests pass

**Checkpoint**: At this point, forged JWT tokens can no longer bypass rate limiting. This is the MVP — the most critical vulnerability is fixed.

---

## Phase 4: User Story 2 - Opaque Error Responses in Production (Priority: P2)

**Goal**: Remove `error_type` and `message` fields from the global 500 exception handler response, preventing internal state leakage to clients.

**Independent Test**: Trigger a 500 error and inspect the response body — it should contain only `{"detail": "Internal Server Error"}` with no additional fields.

### Implementation for User Story 2

- [ ] T008 [US2] Remove `error_type` and `message` keys from the `content` dict in the `global_exception_handler` function (lines 118-122), leaving only `{"detail": "Internal Server Error"}` in `gateway/main.py`
- [ ] T009 [US2] Verify the `print()` and `traceback.print_exc()` calls (lines 114-115) are preserved so server-side logging is unaffected in `gateway/main.py`
- [ ] T010 [US2] Check `tests/test_main_unit.py` for any assertions on `error_type` or `message` fields and update if present in `tests/test_main_unit.py`
- [ ] T011 [US2] Run `python -m pytest tests/test_main_unit.py tests/test_main_lifespan.py -v` and verify all main module tests pass

**Checkpoint**: At this point, 500 error responses no longer leak internal state. Server-side logging remains intact.

---

## Phase 5: User Story 3 - Hardened Contract Compilation Subprocess (Priority: P3)

**Goal**: Add explicit `shell=False` to the `subprocess.run()` call in the contract compilation function as defense-in-depth.

**Independent Test**: Verify contract compilation continues to work correctly and inspect the code to confirm `shell=False` is present.

### Implementation for User Story 3

- [ ] T012 [US3] Add `shell=False` parameter to the `subprocess.run()` call on line 287-290 of the `compile_escrow_contract()` function in `gateway/algod_client.py`
- [ ] T013 [US3] Run `python -m pytest tests/test_algod_client.py -v` and verify all algod client tests pass

**Checkpoint**: All three security hardening stories are now complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full regression verification and cleanup

- [ ] T014 Run the full test suite with `python -m pytest tests/ -v` to verify no regressions across all modules
- [ ] T015 Run quickstart.md validation scenarios to confirm end-to-end behavior matches expectations
- [ ] T016 Review all modified files for any leftover debug statements, comments referencing the old regex check, or TODO markers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 verification
- **User Stories (Phase 3-5)**: All depend on Phase 1 verification only
  - All three user stories modify **different files** and can proceed in parallel
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 1 — modifies `gateway/rate_limiter.py` and `tests/test_rate_limiter.py`
- **User Story 2 (P2)**: Can start after Phase 1 — modifies `gateway/main.py` and `tests/test_main_unit.py`
- **User Story 3 (P3)**: Can start after Phase 1 — modifies `gateway/algod_client.py`
- **No cross-story dependencies**: Each story touches entirely different files

### Within Each User Story

- Implementation before test updates (since we're fixing existing code, not writing new code TDD-style)
- Verify tests pass before moving to next story

### Parallel Opportunities

- T003 (US1), T008 (US2), and T012 (US3) can all run in parallel — they modify different files
- T004, T005, T006 (US1 test updates) can run in parallel with T010 (US2 test check) — different test files

---

## Parallel Example: All Three Stories

```bash
# All three stories can run concurrently since they modify different files:
Agent A: T003 → T004 → T005 → T006 → T007  (gateway/rate_limiter.py + tests/test_rate_limiter.py)
Agent B: T008 → T009 → T010 → T011          (gateway/main.py + tests/test_main_unit.py)
Agent C: T012 → T013                         (gateway/algod_client.py + tests/test_algod_client.py)

# Then converge for Polish:
All: T014 → T015 → T016
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Verify pre-conditions
2. Complete Phase 3: Fix rate limiter JWT bypass
3. **STOP and VALIDATE**: Run rate limiter tests independently
4. Deploy — the most critical vulnerability is now patched

### Incremental Delivery

1. Verify setup → Foundation ready
2. Fix rate limiter bypass (US1) → Test → Most critical vulnerability patched
3. Fix info leakage (US2) → Test → Second vulnerability patched
4. Harden subprocess (US3) → Test → Defense-in-depth complete
5. Full regression → All hardening complete

### Parallel Team Strategy

With multiple developers:

1. Verify setup together
2. Once Phase 1 verified:
   - Developer A: User Story 1 (rate_limiter.py)
   - Developer B: User Story 2 (main.py)
   - Developer C: User Story 3 (algod_client.py)
3. Stories complete and verify independently, then full regression

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- The existing test on line 75 of `test_rate_limiter.py` that asserts fake JWT bypass is the key test to invert
- Commit after each user story checkpoint
- Stop at any checkpoint to validate story independently
