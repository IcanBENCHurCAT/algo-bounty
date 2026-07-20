## 2026-07-16 - [Fix] Remove Unused resolve_did_public_key
**Vulnerability:** Server-Side Request Forgery (SSRF) in `gateway/crypto.py` `resolve_did_public_key`. The function accepted an arbitrary `did:web:` URI and fetched its `.well-known/did.json` document without validating if the destination domain or IP resolved to an internal, private network (e.g., `127.0.0.1`, `169.254.169.254`).
**Learning:** Functions that parse user-provided URLs/DIDs and make outbound HTTP requests must implement robust domain and IP whitelisting or local-address blocking to prevent SSRF, even if the scheme is hardcoded to `https`. Unused code is a liability.
**Prevention:** Remove dead/unused code to reduce attack surface. For active code, use libraries like `advocate` or implement strict IP checking (reject RFC 1918, RFC 4193, RFC 6890 addresses) before dispatching the `httpx` request.

## 2026-07-20 - [Fix] Fix Timing Attack in Webhook API Key Authentication
**Vulnerability:** A Timing Attack vulnerability was present in `gateway/middleware/middleware.py`. The `WebhookApiKeyAuthMiddleware` class validated API keys using a simple equality check (`!=`), which exits early on the first mismatching character. This allows an attacker to deduce a valid API key by measuring response times.
**Learning:** Security-sensitive string comparisons like tokens, secrets, or API keys should never use simple equality operators, as it leaks information about the secret through timing variations.
**Prevention:** Always use constant-time comparison functions such as `secrets.compare_digest` or `hmac.compare_digest` when verifying secrets, passwords, tokens, or API keys.
