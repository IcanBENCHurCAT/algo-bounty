# ADR 0001: Gateway Security & GitHub Validation

**Date**: 2026-07-19

**Status**: Accepted

## Context
As the AlgoBounty platform integrates trustless GitHub automated payouts and scales its FastAPI gateway, several operational and security vulnerabilities were identified in early reviews (Specs 002 and 003):
1. **Rate Limiting & Authentication**: The gateway's rate limiter was only checking the format of JWTs using a regex, failing to cryptographically verify them. This allowed an attacker to bypass rate limits by forging fake tokens.
2. **Information Leakage**: The global exception handler returned internal exception types and messages on 500 errors.
3. **Command Injection Risks**: Contract compilation was executing via `subprocess.run` without explicitly disabling shell execution.
4. **GitHub Trustless Flow**: Trustless bounties (`is_hitm = 0`) needed a secure, idempotent way to process `pull_request.merged` webhooks to automatically release escrow funds without risking duplicate payouts.

## Decision
We will implement the following security and validation enhancements in the gateway:
1. **Cryptographic JWT Verification**: The rate limiter middleware must cryptographically verify JWT tokens using the platform's signing keys before granting any rate-limit exemptions. Invalid tokens will silently fall back to IP-based rate limiting.
2. **Opaque Error Handling**: The global exception handler will be modified to return generic `{"detail": "Internal Server Error"}` messages for all unhandled 500-level exceptions, while still logging the full stack trace server-side.
3. **Hardened Subprocesses**: Enforce `shell=False` for all subprocess executions (e.g., contract compilation) to prevent command injection.
4. **Idempotent Webhooks & Signatures**: The GitHub webhook receiver (`/webhooks/github`) must validate all incoming payloads using HMAC-SHA256 signatures against the configured webhook secret. Additionally, we will implement idempotency checks (via delivery ID tracking) to ensure that multiple webhook deliveries for a single PR merge only trigger one on-chain payout transaction.

## Consequences
- **Positive**: Eliminates critical rate-limiting bypass vulnerabilities and internal state leakage. Ensures trustless payouts are secure and immune to duplicate execution from GitHub webhook retries.
- **Negative**: Adds overhead to the rate limiter (JWT crypto verification on every request). Webhook processing requires maintaining a cache or sync table for idempotency, increasing database/Redis dependency complexity.
