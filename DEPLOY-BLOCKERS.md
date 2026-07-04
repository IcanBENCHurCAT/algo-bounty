# AlgoBounty — Deploy Blockers

**Last updated:** 2026-07-03

## 🔴 Must-fix before staging or production merge

### 1. `SECRET_KEY` — Gateway crashes without it
- **Where:** `gateway/auth.py` — startup raises if missing
- **Fix:** Set a strong random key in env (staging + prod)
- **Risk:** Complete gateway failure if omitted

### 2. `PLATFORM_PRIVATE_KEY` — Can't create bounty escrows
- **Where:** `gateway/algod_client.py` — `get_default_account()` expects it
- **Fix:** Set the platform wallet private key in env
- **Risk:** Bounty creation silently fails or crashes

### 3. `GITHUB_WEBHOOK_SECRET` — Webhooks rejected in production
- **Where:** `gateway/github.py` `validate_webhook()` — rejects if missing in non-sandbox
- **Fix:** Generate a random webhook secret, set in env
- **Risk:** GitHub webhook callbacks silently dropped

### 4. `WEBHOOK_API_KEY` — Extra gate on webhook endpoints (NEW)
- **Where:** `gateway/middleware.py` `WebhookApiKeyAuthMiddleware`
- **What it does:** Requires `X-API-Key` header on `/webhooks/*` paths. Defense-in-depth — even if webhook URL is exposed, callers need this key.
- **Fix:** Set a random API key in env, configure webhook client to pass `X-API-Key` header
- **Risk:** Webhook calls return 401

### 5. Alembic migrations — New schema changes not applied
- **Where:** `gateway/alembic.ini`, `gateway/supabase_migration.py`
- **Fix:** Run `alembic -c gateway/alembic.ini upgrade head` against staging DB before deploy
- **Risk:** Missing tables/indexes, stricter nullability constraints will cause errors

### 6. Escrow timing change — microseconds → seconds
- **Where:** `escrow.algo` — `DISPUTE_TIMEOUT`, `CLAIM_TIMEOUT`, `DEFAULT_HITM_REVIEW_WINDOW`
- **Fix:** Review deployed on-chain contract state, verify new unit expectations are compatible
- **Risk:** If previous on-chain contracts expected microseconds, they may time out instantly or not at all under the new seconds-based system

## 🟡 Should fix but not blocking launch

### 7. GitHub App creation (optional, fallback works)
- **What:** Create a GitHub App on the repo for better rate limits and permissions
- **Fallback:** Personal access token (`GITHUB_TOKEN`) works for now
- **Requires:** `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`, `GITHUB_INSTALLATION_ID`
- **Priority:** Low — can ship with PAT, upgrade later

### 8. SSE broker tuning
- **Where:** `gateway/broker.py` `EventBroker` — `MAX_CONNECTIONS_PER_IP`
- **Fix:** Validate that limits match expected dashboard traffic
- **Risk:** Connections rejected under heavy load

## Quick env checklist for deploy target

```bash
SECRET_KEY=***              # Required — gateway won't start without it
PLATFORM_PRIVATE_KEY=***    # Required — can't create escrow without it
GITHUB_WEBHOOK_SECRET=***   # Required — webhooks rejected otherwise
WEBHOOK_API_KEY=***         # Required — new middleware gate
GITHUB_TOKEN=***            # Optional but recommended — PAT fallback works
CORS_ALLOW_ORIGINS=***      # TODO: env var for CORS domains (not yet implemented)
ALGORAND_NETWORK=testnet    # Required — which chain to use
SUPABASE_URL=***            # Required — DB connection
SUPABASE_SERVICE_ROLE_KEY=*** # Required — DB access
```

## Migration steps (staging first)

1. Set all env vars above on staging
2. Run Alembic: `alembic -c gateway/alembic.ini upgrade head`
3. Verify `/health` endpoint returns healthy
4. Test bounty creation flow end-to-end
5. Test webhook callback (use ngrok or GitHub test webhook config)
6. Review escrow timing — verify deployed contract compatibility
7. If all green → merge to production
