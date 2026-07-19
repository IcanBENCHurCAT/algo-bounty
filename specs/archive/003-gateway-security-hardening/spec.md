# Feature Specification: Gateway Security Hardening

**Feature Branch**: `003-gateway-security-hardening`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Security audit revealed critical vulnerabilities in the AlgoBounty gateway: (1) Rate limiter JWT bypass — the middleware validates JWT format with a regex but never cryptographically verifies the token, allowing attackers to bypass all rate limits with a fake Bearer header. (2) Information leakage — the global exception handler returns internal error types and exception messages to clients. (3) Subprocess safety — contract compilation uses subprocess.run without explicit shell=False."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rate Limit Enforcement Against Forged Tokens (Priority: P1)

An unauthenticated attacker attempts to bypass API rate limits by sending a forged `Authorization: Bearer aaa.bbb.ccc` header. The system cryptographically validates the token before granting rate-limit exemptions, so the forged token is rejected and the attacker remains subject to IP-based rate limiting. Repeated abuse results in the attacker being throttled and eventually receiving 429 Too Many Requests responses.

**Why this priority**: This is the most critical vulnerability. Without this fix, all rate-limiting protections are effectively disabled for anyone who crafts a trivial fake token. This opens the platform to brute-force authentication attacks, denial-of-service via endpoint flooding, and enumeration attacks on bounty data.

**Independent Test**: Can be fully tested by sending requests with fake Bearer tokens and verifying they are rate-limited, while requests with legitimately signed tokens continue to bypass rate limits as intended.

**Acceptance Scenarios**:

1. **Given** a request with `Authorization: Bearer aaa.bbb.ccc` (syntactically valid but unsigned), **When** the request reaches the rate limiter middleware, **Then** the request is treated as unauthenticated and subject to IP-based rate limiting.
2. **Given** a request with a legitimately signed JWT issued by the platform, **When** the request reaches the rate limiter middleware, **Then** the request bypasses IP-based rate limiting as before.
3. **Given** a request with an expired but otherwise valid JWT, **When** the request reaches the rate limiter middleware, **Then** the request is treated as unauthenticated and subject to IP-based rate limiting.
4. **Given** an attacker sending 100 requests per second with forged tokens to `/api/v1/auth/request`, **When** the rate limiter evaluates each request, **Then** requests exceeding the configured threshold (5 req/min for unauthenticated users) receive 429 responses.

---

### User Story 2 - Opaque Error Responses in Production (Priority: P2)

When an unhandled exception occurs in the gateway (e.g., a database connection failure, an unexpected null reference, or a malformed blockchain response), the system returns a generic "Internal Server Error" message to the client without revealing the exception class name, exception message, or any internal application state. Server-side logs still capture the full error details for debugging.

**Why this priority**: Information leakage helps attackers map internal architecture, identify technology versions, and discover exploitable paths. While less immediately exploitable than the rate-limit bypass, this is a well-known OWASP vulnerability (Improper Error Handling) that should be addressed promptly.

**Independent Test**: Can be fully tested by triggering server errors and inspecting the response body to confirm it contains only a generic message, while verifying that server logs still contain the full exception details.

**Acceptance Scenarios**:

1. **Given** an unhandled exception occurs during request processing, **When** the global exception handler catches it, **Then** the response body contains only `{"detail": "Internal Server Error"}` with no additional fields.
2. **Given** the same unhandled exception, **When** the global exception handler catches it, **Then** the full exception type, message, and stack trace are written to server-side error logs.
3. **Given** a client receives a 500 response, **When** they inspect the response body, **Then** they cannot determine the type of error, the technology stack, or any internal file paths.

---

### User Story 3 - Hardened Contract Compilation Subprocess (Priority: P3)

When the platform compiles an escrow contract via an external process, the system explicitly prevents shell injection by enforcing non-shell execution mode. This ensures that even if future code changes introduce dynamic path resolution, the subprocess call cannot be exploited for command injection.

**Why this priority**: The current implementation is relatively safe due to hardcoded paths and list-based arguments. This is a defense-in-depth measure to prevent future regressions rather than an active exploit fix.

**Independent Test**: Can be tested by verifying the subprocess call configuration and confirming that shell execution is explicitly disabled, and that contract compilation continues to work correctly.

**Acceptance Scenarios**:

1. **Given** the contract compilation function is invoked, **When** the subprocess executes, **Then** the execution mode explicitly prevents shell interpretation of arguments.
2. **Given** the contract compilation function is invoked with a valid contract, **When** the subprocess completes, **Then** the compiled output is produced successfully (no regression).

---

### Edge Cases

- What happens when the JWT verification function itself throws an unexpected error (e.g., missing SECRET_KEY configuration)? The rate limiter should treat the request as unauthenticated rather than crashing.
- What happens when the Authorization header contains a valid JWT format but the signing algorithm is `none`? The system should reject it.
- What happens when the error response is for a validation error (e.g., 422) versus an unhandled exception (500)? Only unhandled 500 errors should be made opaque; expected error responses (4xx) should continue to include descriptive messages.
- What happens when rate limiting is evaluated during CI tests with `TESTING="True"`? Rate limit behavior in tests should remain consistent with the existing CI bypass mechanisms.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The rate limiter middleware MUST cryptographically verify JWT tokens before granting rate-limit exemptions, using the same verification logic as the authentication system.
- **FR-002**: The rate limiter MUST treat any request with an invalid, expired, or malformed JWT as unauthenticated for rate-limiting purposes.
- **FR-003**: The rate limiter MUST NOT crash or return an error if JWT verification fails; it MUST silently fall through to IP-based rate limiting.
- **FR-004**: The global exception handler MUST return only `{"detail": "Internal Server Error"}` in the response body for unhandled exceptions, with no error type, message, or stack trace information.
- **FR-005**: The global exception handler MUST continue to log the full exception details (type, message, traceback) to server-side error logs.
- **FR-006**: The contract compilation subprocess MUST explicitly disable shell execution mode to prevent command injection.
- **FR-007**: All existing API behavior for legitimately authenticated users MUST remain unchanged after security hardening.
- **FR-008**: The rate limiter MUST handle edge cases gracefully, including missing configuration, algorithm confusion attacks (e.g., `alg: none`), and malformed headers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of requests with forged or invalid JWT tokens are subject to IP-based rate limiting (zero bypass rate for unauthenticated users).
- **SC-002**: 100% of 500-level error responses contain only the generic error message, with zero information leakage of internal state.
- **SC-003**: Legitimately authenticated users experience zero change in rate-limit behavior or API response times.
- **SC-004**: All existing automated tests continue to pass after security hardening changes.
- **SC-005**: Server-side error logs retain full exception details for all caught exceptions, enabling unimpaired debugging.

## Assumptions

- The existing `verify_jwt_token` function in the authentication module is the canonical source of truth for JWT validation and will be reused by the rate limiter.
- The JWT signing key (`SECRET_KEY`) is already available in the middleware's execution context via the gateway configuration.
- Rate-limit bypass for CI tests (`TESTING="True"`) is handled separately and is unaffected by JWT verification changes.
- The contract compilation fix is a defense-in-depth measure; no active exploit path currently exists for the subprocess call.
- Expected error responses (4xx status codes like 400, 401, 404, 422) will continue to include descriptive error messages — only unhandled 500 errors are made opaque.
