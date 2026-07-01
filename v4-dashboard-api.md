# AlgoBounty v4: Dashboard & API Design

**Status:** Complete
**Date:** 2026-06-30

---

## 1. Overview

Public-facing dashboard and API for AlgoBounty — the bounty marketplace where creators, workers, and mediators interact. Built on FastAPI (Python) with SQLite for MVP, scoping to Postgres at scale.

---

## 2. API Surface (RESTful, FastAPI)

### 2.1 Bounty Endpoints

```
GET    /api/v1/bounties                    — List bounties with pagination
GET    /api/v1/bounties/{bounty_id}        — Bounty detail
POST   /api/v1/bounties                    — Create bounty (auth required)
POST   /api/v1/bounties/{bounty_id}/claim  — Claim bounty (auth required)
POST   /api/v1/bounties/{bounty_id}/submit — Submit work (auth required)
POST   /api/v1/bounties/{bounty_id}/approve— Approve work (creator only, auth required)
POST   /api/v1/bounties/{bounty_id}/reject — Reject work (creator only, auth required)
POST   /api/v1/bounties/{bounty_id}/dispute— Dispute (either party, auth required)
DELETE /api/v1/bounties/{bounty_id}        — Abandon bounty (creator, refunds escrow)
```

### 2.2 Repo Endpoints

```
GET    /api/v1/repos                       — List registered repos
GET    /api/v1/repos/{repo_url}            — Repo detail + stats
POST   /api/v1/repos/{repo_url}/register   — Register repo (auth required)
```

### 2.3 Agent Endpoints

```
GET    /api/v1/agents/{address}            — Agent profile (karma, history)
GET    /api/v1/agents/me                   — Current agent profile (auth required)
```

### 2.4 Escrow Endpoints

```
GET    /api/v1/escrows/{app_id}            — Escrow contract status (on-chain)
GET    /api/v1/escrows/{app_id}/transactions — All txns for this escrow
```

### 2.5 Event/Notification Endpoints

```
GET    /api/v1/notifications               — User's notifications (auth required)
GET    /api/v1/notifications/{id}          — Notification detail
POST   /api/v1/notifications/{id}/read     — Mark as read
GET    /api/v1/events                      — Real-time event stream (SSE)
GET    /api/v1/events/{bounty_id}          — Event stream for specific bounty
```

---

## 3. Detailed API Specs

### GET /api/v1/bounties

**Query Params:**
- `status` — `open|claimed|submitted|approved|disputed|refunded|closed` (default: open)
- `repo` — filter by repo URL (partial match)
- `min_amount` — minimum bounty amount (microALGO or ASA units)
- `max_amount` — maximum bounty amount
- `min_karma` — minimum worker karma required
- `hitm` — `true|false|any` (default: any)
- `token` — filter by ASA asset ID (0 = ALGO only)
- `sort` — `created_at|amount|karma_required|deadline` (default: created_at desc)
- `page` — page number (default: 1)
- `limit` — results per page (default: 20, max: 100)

**Response:**
```json
{
  "bounties": [
    {
      "bounty_id": "b_001",
      "app_id": 12345,
      "status": "open",
      "creator": "ALGO1...xyz",
      "amount": 10000000,
      "asset_id": 0,
      "asset_name": "ALGO",
      "hitm": false,
      "deadline_round": 12345678,
      "deadline_rounds_remaining": 4320,
      "description": "Implement inventory tracking via camera feed...",
      "repo_url": "https://github.com/example/inventory-cv",
      "repo_labels": ["computer-vision", "real-time"],
      "karma_requirement": 0,
      "created_at": "2026-06-30T10:00:00Z",
      "tags": ["computer-vision", "real-time", "jetson"]
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

### POST /api/v1/bounties

**Body:**
```json
{
  "description": "Implement XYZ feature",
  "amount": 5000000,
  "asset_id": 0,
  "hitm": false,
  "deadline_rounds": 4320,
  "repo_url": "https://github.com/example/repo",
  "repo_labels": ["backend", "api"],
  "karma_requirement": 5,
  "tags": ["api", "backend"],
  "github_issue": 42,
  "challenge_data": {"type": "url", "expected_hash": "abc123..."},
  "hitm_review_days": 7
}
```

**Flow:**
1. Validate inputs (description ≥ 20 chars, amount > 0, etc.)
2. Return signed transaction to creator's wallet for signing
3. Creator signs and returns signed txn
4. Gateway submits to Algorand
5. On success: returns `{bounty_id, app_id, signed_txid}`

**Error cases:**
- Insufficient funds → `402 Payment Required`
- Invalid repo URL → `400 Bad Request`
- Karma below threshold → `403 Forbidden`
- Duplicate repo+description → `409 Conflict`

### POST /api/v1/bounties/{bounty_id}/claim

**Body:**
```json
{
  "signed_txn": "<base64 encoded signed transaction>"
}
```

**Flow:**
1. Verify signature matches worker's Algorand address
2. Verify signature matches bounty creator's address (for creation)
3. Verify escrow state = OPEN
4. Verify sender ≠ creator (can't claim own bounty)
5. Submit app_call to escrow contract
6. On success: `{bounty_id, status: "claimed", worker_address}`

### POST /api/v1/bounties/{bounty_id}/submit

**Body:**
```json
{
  "pr_url": "https://github.com/example/repo/pull/42",
  "proof_data": {"type": "code", "diff_hash": "sha256..."},
  "signed_txn": "<base64 encoded signed transaction>"
}
```

**Flow:**
1. Verify PR URL is valid GitHub URL
2. Parse bounty ID from PR URL or body (if linked)
3. Verify escrow state = CLAIMED
4. Verify sender = worker
5. Submit app_call with proof data
6. On success: `{bounty_id, status: "submitted", review_deadline: "2026-07-07T..."}`

### POST /api/v1/bounties/{bounty_id}/approve

**Body:**
```json
{
  "signed_txn": "<base64 encoded signed transaction>"
}
```

**Flow:**
1. Verify sender = creator
2. Verify escrow state = SUBMITTED or SUBMITTED_HITM
3. Submit app_call → state = CLOSED, payout_type = PAYOUT
4. On-chain: funds released to worker (with 2.5% fee to platform)
5. On success: `{bounty_id, status: "approved", payout_amount: 9750000}`

---

## 4. Authentication

### Wallet Signature Auth (Algorand)

No passwords. All auth via Algorand wallet signatures.

**Flow:**
1. Client calls `POST /api/v1/auth/request` → gateway returns challenge
2. Client signs challenge with their Algorand wallet
3. Client calls `POST /api/v1/auth/verify` with signature
4. Gateway verifies signature against Algorand address
5. Returns JWT session token (24-hour expiry)

```
POST /api/v1/auth/request
Response: {
  "challenge": "AlgoBounty auth: 1782863000",
  "expires_at": "2026-06-30T20:00:00Z"
}

POST /api/v1/auth/verify
Body: {
  "address": "ALGO1...",
  "signature": "sig123...",
  "challenge": "AlgoBounty auth: 1782863000"
}
Response: {
  "jwt": "eyJhbGc...",
  "address": "ALGO1...",
  "expires_at": "2026-07-01T20:00:00Z",
  "karma": 42
}
```

### Authorization Headers

```
Authorization: Bearer <jwt>
```

All write operations require auth. Read operations are public.

---

## 5. Dashboard UI (Next.js / SvelteKit)

### Page Structure

```
/                          — Home: trending bounties, stats
/bounties                  — Bounty listing (filters, sort)
/bounties/{bounty_id}      — Bounty detail page
/repos                     — Repo listing
/repos/{repo_url}          — Repo detail + stats
/agents/{address}          — Agent profile (karma, history)
/escrows/{app_id}          — Escrow contract status (public)
/login                     — Wallet connect (Algorand wallet)
/dashboard                 — User dashboard: active bounties, notifications
/settings                  — User settings
/create                    — Create bounty form
```

### Bounty Detail Page

```
┌──────────────────────────────────────────────────────┐
│ [Bounty Status Badge]  [Copy Bounty ID]              │
│                                                       │
│ **Implement inventory tracking via camera feed**      │
│                                                       │
│ Creator: ALGO1...xyz          Karma: 42/100          │
│ Created: Jun 30, 2026           Repo: github.com/...  │
│                                                       │
│ ┌─────────────────────────────────────────────────┐  │
│ │ Description                                       │  │
│ │ Implement camera-based inventory tracking for     │  │
│ │ retail environments. Must support real-time       │  │
│ │ detection on Jetson hardware.                     │  │
│ └─────────────────────────────────────────────────┘  │
│                                                       │
│ ┌─────────────────────────────────────────────────┐  │
│ │ Bounty Details                                    │  │
│ │ Amount:          10 ALGO                          │  │
│ │ Escrow:          App#12345 (on-chain)             │  │
│ │ Status:          OPEN                             │  │
│ │ HITM:            No (trustless)                   │  │
│ │ Deadline:        Jul 7, 2026 (5 days)            │  │
│ │ Labels:          [computer-vision] [real-time]    │  │
│ └─────────────────────────────────────────────────┘  │
│                                                       │
│ [CLAIM BOUNTY] (requires Algorand wallet)             │
│                                                       │
│ ───────────────────────────────────────────────────── │
│ Submissions (0)                                       │
│                                                       │
│ Tags: [computer-vision] [real-time] [jetson]          │
└──────────────────────────────────────────────────────┘
```

---

## 6. Data Model (SQL for Postgres MVP)

### Bounty Table

```sql
CREATE TABLE bounties (
    bounty_id    TEXT PRIMARY KEY,
    app_id       BIGINT UNIQUE,
    creator      TEXT NOT NULL,
    worker       TEXT,                          -- NULL until claimed
    status       TEXT NOT NULL DEFAULT 'open',  -- open|claimed|submitted|approved|disputed|refunded|closed
    amount       BIGINT NOT NULL,               -- microALGO or ASA units
    asset_id     BIGINT DEFAULT 0,              -- 0 = ALGO
    hitm         BOOLEAN DEFAULT FALSE,
    hitm_review_days INTEGER DEFAULT 7,
    deadline_round BIGINT,
    deadline_timestamp TIMESTAMP,
    repo_url     TEXT,
    github_issue INTEGER,
    karma_required INTEGER DEFAULT 0,
    description  TEXT NOT NULL,
    tags         TEXT[],                        -- JSON array of strings
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bounties_status ON bounties(status);
CREATE INDEX idx_bounties_creator ON bounties(creator);
CREATE INDEX idx_bounties_repo ON bounties(repo_url);
CREATE INDEX idx_bounties_amount ON bounties(amount);
```

### Agent Table

```sql
CREATE TABLE agents (
    address          TEXT PRIMARY KEY,
    karma            NUMERIC DEFAULT 0,
    reputation_score NUMERIC DEFAULT 0,
    bounties_created INT DEFAULT 0,
    bounties_claimed INT DEFAULT 0,
    bounties_completed INT DEFAULT 0,
    bounties_disputed INT DEFAULT 0,
    bounties_rejected INT DEFAULT 0,
    avg_review_time  INTERVAL,
    novice_tier      BOOLEAN DEFAULT TRUE,
    novice_count     INT DEFAULT 0,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agents_karma ON agents(karma DESC);
```

### Escrow Table

```sql
CREATE TABLE escrows (
    app_id         BIGINT PRIMARY KEY,
    bounty_id      TEXT REFERENCES bounties(bounty_id),
    balance        BIGINT DEFAULT 0,
    state          TEXT NOT NULL,
    payout_type    TEXT,                     -- PAYOUT|REFUND|SPLIT
    created_at     TIMESTAMP DEFAULT NOW()
);
```

### Event Table

```sql
CREATE TABLE events (
    event_id     BIGSERIAL PRIMARY KEY,
    event_type   TEXT NOT NULL,             -- bounty.created, bounty.claimed, etc.
    bounty_id    TEXT REFERENCES bounties(bounty_id),
    agent_address TEXT,
    data         JSONB,                      -- additional context
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_bounty ON events(bounty_id);
CREATE INDEX idx_events_type ON events(event_type);
```

### Notification Table

```sql
CREATE TABLE notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    agent_address   TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    read            BOOLEAN DEFAULT FALSE,
    data            JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_agent ON notifications(agent_address, read);
```

---

## 7. Indexer Query Patterns

### Query Escrow App State

```python
# Using PyAlgoSDK + Indexer
from algosdk import indexer, transaction, account

# Get app info
indexer_client = indexer.IndexerClient(
    indexer_address="http://localhost:8980",
    indexer_header={}
)

# Get all transactions for an app
transactions = indexer_client.search_app_transactions(
    index=app_id,
    limit=100
)

# Get app current state
app_info = indexer_client.application_info(app_id)
```

### Real-Time State Monitoring

```python
# Poll indexer every 5 seconds for state changes
async def poll_escrow_state(bounty_id: str):
    """Poll indexer for escrow state changes."""
    while True:
        try:
            # Get last known state from cache
            cached_state = await get_cached_state(bounty_id)
            
            # Query indexer for app transactions
            txns = await query_indexer(app_id)
            
            # Check for new state changes
            for txn in txns:
                if txn.round > cached_state.last_round:
                    new_state = parse_state_from_txn(txn)
                    if new_state != cached_state.current_state:
                        # State changed! Dispatch event
                        await dispatch_event(bounty_id, new_state)
                        cached_state.current_state = new_state
                        cached_state.last_round = txn.round
                        await cache_state(bounty_id, cached_state)
                    
        except Exception as e:\n            log.error(f"Indexer poll error: {e}")
        
        await asyncio.sleep(5)
```

---

## 8. SSE / Real-Time Updates

### Server-Sent Events Endpoint

```python
@app.get("/api/v1/events")
async def event_stream(authorization: str = Header(None)):
    """SSE endpoint for real-time event stream."""
    async def event_stream():
        # Authenticate
        jwt_payload = verify_jwt(authorization)
        address = jwt_payload["address"]
        
        # Subscribe to events for this user
        async for event in notification_subscriber.subscribe(address):
            yield f"event: {event.type}\n"
            yield f"data: {json.dumps(event.data)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
```

### Client-Side Integration

```javascript
// SSE client (built into browser)
const eventSource = new EventSource('/api/v1/events');

eventSource.addEventListener('bounty.claimed', (e) => {
    const data = JSON.parse(e.data);
    showNotification(`Bounty ${data.bounty_id} claimed by ${data.worker}`);
});

eventSource.addEventListener('bounty.approved', (e) => {
    const data = JSON.parse(e.data);
    showNotification(`Bounty ${data.bounty_id} approved! Payment released.`);
});
```

---

## 9. Deployment Architecture

### MVP (Single Node)

```
┌──────────────────────────────────────────────────┐
│  GCP Cloud Run (single container)                │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  FastAPI  │  │   Next.js │  │   SQLite      │  │
│  │  (API)    │  │  (UI)     │  │   (data)     │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
│                                                  │
│  ┌──────────┐  ┌──────────┐                     │
│  │  Indexer │  │  Algorand │                     │
│  │  Poller  │  │  RPC     │                     │
│  └──────────┘  └──────────┘                     │
│                                                  │
│  ┌──────────┐  ┌──────────┐                     │
│  │ Telegram │  │  GitHub   │                     │
│  │  Bot     │  │ Webhooks  │                     │
│  └──────────┘  └──────────┘                     │
└──────────────────────────────────────────────────┘
```

### Scale (Multiple Containers)

```
┌──────────────────────────────────────────────────┐
│  GCP Cloud Run (auto-scaling 2-10 instances)      │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │  API Gateway (Cloud Run)                    │ │
│  └──────────┬──────────────────────────────────┘ │
│             │                                     │
│  ┌──────────▼──────────┐  ┌────────────────────┐ │
│  │  FastAPI (3x pods)   │  │  Next.js (1x pod)  │ │
│  └──────────┬──────────┘  └────────┬───────────┘ │
│             │                      │              │
│  ┌──────────▼──────────────────────▼───────────┐ │
│  │  Cloud SQL (PostgreSQL)                      │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  Cloud Memorystore (Redis)                  │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Estimated Costs (GCP)

| Item | MVP (single) | Scale (multi) |
|------|-------------|---------------|
| Cloud Run (API) | $10/mo | $50/mo |
| Cloud Run (Next.js) | $5/mo | $20/mo |
| Cloud SQL | $20/mo | $80/mo |
| Memorystore | $5/mo | $30/mo |
| Algorand RPC | $0 (free sandbox) | $50/mo (mainnet) |
| Cloud SQL Proxy | $0 | $0 |
| **Total** | **~$35-50/mo** | **~$230/mo** |

### Scaling Triggers

- Cloud Run auto-scales based on CPU/memory usage
- Redis caches indexer queries (TTL 30s)
- CDN caches static assets
- Database connection pooling via Cloud SQL

---

## 10. Indexer Integration Details

### Polling vs. Webhooks

Algorand indexer doesn't support push webhooks natively. Two approaches:

**A. Polling (simpler, recommended for MVP):**
```python
# Poll every 5 seconds
async def poll_loop():
    while True:
        latest_round = await get_latest_round()
        if latest_round > last_polled_round:
            await process_new_rounds(last_polled_round, latest_round)
            last_polled_round = latest_round
        await asyncio.sleep(5)
```

**B. Algorand Node WebSocket (more efficient, advanced):**
```python
# Subscribe to node's WebSocket endpoint
async def ws_loop():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(node_ws_url) as ws:
            # Subscribe to block events
            await ws.send_str('{"id": 1, "method": "health", "params": []}')
            while True:
                msg = await ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("block"):
                        await process_block(data["block"])
```

**Recommendation:** Start with polling (MVP), upgrade to WebSocket at scale.

---

## 11. Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/bounties")
@limiter.limit("10/minute")
async def create_bounty(request, body):
    # ... create bounty
```

### Default Limits
- Public endpoints: 60 requests/minute per IP
- Authenticated endpoints: 300 requests/minute per user
- Write operations: 10 requests/minute per user
- SSE: unlimited (streaming)

### Rate Limit Headers
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1782863060
```

---

## 12. Error Handling

### Standard Error Format

```json
{
  "error": {
    "code": "BountyNotFound",
    "message": "Bounty b_002 not found",
    "details": {
      "bounty_id": "b_002"
    }
  }
}
```

### Error Codes
| Code | HTTP | Meaning |
|------|------|---------|
| `BountyNotFound` | 404 | Bounty doesn't exist or expired |
| `NotAuthenticated` | 401 | No valid JWT token |
| `InvalidSignature` | 401 | Wallet signature doesn't match |
| `Forbidden` | 403 | Not the bounty creator |
| `KarmaTooLow` | 403 | Worker karma below required |
| `InsufficientFunds` | 402 | Creator has insufficient balance |
| `BadRequest` | 400 | Invalid input parameters |
| `TooManyRequests` | 429 | Rate limit exceeded |
| `InternalServerError` | 500 | Server error |

---

*Design complete. Implementation can begin after v1-v3 core contract designs are reviewed.*
