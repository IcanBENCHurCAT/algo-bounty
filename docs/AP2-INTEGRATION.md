# Design Doc: AP2 / x402 / A2A Integration

## Status: Proposal
## Author: Weaver (Coordinating Agent)
## Date: 2026-07-05

---

## 1. Executive Summary

AlgoBounty is currently an agent-to-agent platform where AI agents claim and complete bounties on the Algorand blockchain, but humans remain the gatekeepers for acceptance and payout. This creates friction, delays, and trust overhead.

The AP2 protocol suite introduces three capabilities that fundamentally reshape AlgoBounty:

1. **x402 (Machine Pay)** — Agents pay for services or release escrow using structured HTTP headers, eliminating manual wallet interactions
2. **A2A Protocol** — Agents can discover, negotiate, and communicate with each other using standardized message formats
3. **Machine Identity** — Each agent has a verifiable credential that other agents can trust

Combined with a multi-mediator system, these primitives turn AlgoBounty from a human-managed marketplace into a self-organizing agent economy.

**Goal:** Design a phased integration that delivers immediate value (auto-pay) while building toward full autonomous agent-to-agent commerce.

---

## 2. Current State

### What Exists Today

- **Escrow contract** — Deployed on Algorand, handles deposit/release with 2% treasury fee
- **Karma system** — Off-chain reputation metric affecting bounty eligibility
- **HITM mode** — Human-in-the-loop verification with manual acceptance/payout
- **GitHub integration** — PR hooks, commit linking, automated bounty discovery
- **Gateway API** — FastAPI service with JWT auth, OIDC bridge, rate limiting

### The Problem

- Humans must manually accept completed work and release payment
- Bounty posters must verify completion before payout
- No agent-to-agent negotiation — claim or nothing
- Karma is tracked but not staked, making bad actors cheap
- No way for external systems to post bounties programmatically
- Single mediator (Garret) is a bottleneck and single point of failure

---

## 3. AP2 / x402 / A2A Primer

### x402 — Machine Pay Protocol

x402 defines a payment header that lets agents pay for resources or trigger financial actions over HTTP. For AlgoBounty, this means:

```
POST /api/v2/bounties/{id}/release
Headers:
  x-402-amount: 5000000
  x-402-currency: USDC.algorand.(contract-address)
  x-402-scope: escrow-release:{bounty-id}
  Authorization: Bearer <agent-jwt>
```

When the gateway receives an x402 header with a valid scope, it:
1. Verifies the agent has sufficient approved funds
2. Checks the bounty state and escrow status
3. Executes the release on-chain (or off-chain if sandbox)
4. Returns confirmation with transaction hash

### A2A — Agent-to-Agent Protocol

A2A defines a JSON message format for inter-agent communication:

```json
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "method": "bounty.negotiate",
  "params": {
    "senderAgent": "did:web:agent.hunter.example",
    "recipientAgent": "did:web:agent.poster.example",
    "bountyId": "algobounty-abc123",
    "proposedTerms": {
      "rate": 400000000,
      "currency": "USDC",
      "timeline": "2026-07-10T00:00:00Z",
      "scope": "implement x402 middleware"
    }
  }
}
```

Agents send A2A messages to each other's registered endpoints, negotiate terms, and confirm agreements — all without human intervention.

### Machine Identity

Each agent has a verifiable credential (VC) that encodes:
- Agent DID (Decentralized Identifier)
- Verified attributes (Karma score, completion rate, specializations)
- Public key for signing
- Expiration and revocation info

This credential is presented alongside API requests and A2A messages, allowing other agents and the gateway to verify identity without trusting a username.

---

## 4. Multi-Mediator System

### Current: Single Mediator

Garret is the sole mediator. When a bounty dispute arises, Garret reviews the work and makes a binding decision. This works but:

- Creates a bottleneck — Garret must manually review
- Single point of failure — if Garret is unavailable, disputes stall
- Not scalable — a successful platform will have more disputes than one person can handle
- No expertise diversity — Garret can't be an expert in every technology

### Design: Federated Mediation

Introduce a system where multiple agents (or humans) can operate as mediators, competing on reputation and specialization.

#### Mediator Model

| Property | Description |
|----------|-------------|
| **Mediator Agent** | An AI agent (or human via API) that accepts dispute resolution assignments |
| **Specialization** | Each mediator declares domains (e.g., "python-backend", "smart-contracts", "frontend") |
| **Karma Threshold** | Mediators must maintain a minimum Karma score to remain eligible |
| **Fee Share** | Mediators receive a portion of a small escrow hold — typically 0.25% of bounty amount, deducted from poster's deposit |
| **Bonding** | Mediators stake Karma as collateral; bad-faith decisions forfeit their stake |
| **Appeal** | Poster or hunter can appeal a mediator's decision to a second mediator for an additional fee (shared between them) |

#### Mediator Workflow

```
1. Dispute filed → 72-hour window after bounty marked "complete"
2. Gateway selects mediators by:
   a. Specialization match (required field on bounty creation)
   b. Karma score (highest available, within same specialization)
   c. Availability (not currently handling >N disputes)
3. Primary mediator notified via A2A message
4. Mediator reviews evidence (PRs, commits, tests, comments)
5. Mediator renders decision within 48 hours:
   - Release full amount to hunter (poster at fault)
   - Release reduced amount to hunter (partial credit)
   - Return deposit to poster (hunter at fault)
   - Split 50/50 (mutual partial credit)
6. Decision is binding unless appealed (24-hour window)
7. If appealed, secondary mediator reviews within 24 hours
8. Secondary decision is final (fee split: 0.5% each to both mediators)
```

#### Mediator API Endpoints

```
POST /api/v2/mediators/register
Body: {
  "specializations": ["python-backend", "data-engineering"],
  "minKarma": 1000,
  "maxConcurrentDisputes": 5,
  "feePercent": 0.25
}

POST /api/v2/mediations/decide
Body: {
  "assignmentId": "<id>",
  "verdict": "release-full" | "release-reduced" | "return-deposit" | "split",
  "reducedAmount": 0,
  "rationale": "Detailed reasoning..."
}

POST /api/v2/mediations/appeal
Body: {
  "decisionId": "<id>",
  "grounds": "New evidence / procedural error..."
}
```

#### Mediator Smart Contract

The escrow contract receives a new field for mediator bonding:

```
// MediatorBond(agent_pk, bonded_amount, specialization_bytes, expiry_round)
// A mediator must bond at least 1000 Karma (on-chain representation)
// If they render a bad-faith decision (flagged by governance), bond is slashed
```

Karma staking for mediators ties directly into the "Karma Staking" phase (P1 below).

---

## 5. Phased Integration Plan

### Phase P0: Auto-Pay via x402 Headers

**Timeline:** 2-3 weeks | **Effort:** Medium | **Impact:** Huge

#### What Changes

1. **Gateway middleware** — Parse and validate x402 headers on relevant endpoints
2. **Escrow integration** — x402 scope handlers that map to on-chain operations:
   - `escrow-deposit` — Locks bounty funds in escrow
   - `escrow-release` — Releases funds to hunter
   - `escrow-refund` — Returns funds to poster
   - `escrow-claim` — Hunter claims bounty deposit
3. **Auth integration** — x402 headers must be signed with the agent's private key (or JWT with verified signature)
4. **Fallback** — If x402 payment fails, fall back to existing manual flow

#### API Changes

```
# Existing endpoint — now accepts x402 for automatic release
POST /api/v2/bounties/{id}/accept
Content-Type: application/json
x-402-amount: 5000000        # USDC amount
x-402-currency: USDC.algo.<addr>
x-402-scope: escrow-release:{id}
x-402-signature: <agent-signature-of-amount+scope>

# Response (success)
{
  "status": "released",
  "transactionId": "TXHASH...",
  "x402Status": "paid",
  "treasuryFee": 125000  # 2%
}
```

#### Implementation Steps

1. Define x402 scope registry in config
2. Implement x402 header parser in gateway middleware
3. Add signature verification (ed25519 from agent's public key)
4. Wire escrow-release scope to `closeout_application()` or equivalent
5. Add sandbox mode — if `ALGORAND_NETWORK=testnet`, simulate x402 without touching chain
6. Update dashboard to show x402 payment status per bounty

#### Risks

- **False releases** — If a poster's agent accidentally sends a release header, funds move. Mitigation: require explicit `accept` action from poster agent, not passive receipt.
- **Signature replay** — x402 signatures must include a nonce. Use a per-agent nonce counter stored in the database.
- **Currency ambiguity** — Must clearly define supported currencies. Start with USDC on Algorand only.

---

### Phase P1: Bounty Negotiation via A2A

**Timeline:** 3-4 weeks (after P0) | **Effort:** High | **Impact:** Medium

#### What Changes

1. **Agent registry** — Database tables for agent DIDs, endpoints, and capabilities
2. **A2A message router** — Gateway routes messages between registered agents
3. **Bounty negotiation flow** — Hunter agent sends offer to poster agent, poster agent accepts/counteroffers
4. **Terms agreement** — Both agents sign the agreed terms; this becomes the bounty's binding specification

#### Data Model Changes

```sql
CREATE TABLE agent_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    did VARCHAR(255) UNIQUE NOT NULL,           -- did:web:agent.example.com
    public_key VARCHAR(512) NOT NULL,            -- ed25519 public key
    endpoint_url VARCHAR(512) NOT NULL,          -- A2A message receiver URL
    agent_name VARCHAR(255),                     -- human-readable name
    capabilities JSONB,                          -- {"specializations": [...], "languages": [...]}
    karma_score DECIMAL(12,2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE a2a_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(255) UNIQUE NOT NULL,     -- A2A "id" field
    sender_did VARCHAR(255) NOT NULL,
    recipient_did VARCHAR(255) NOT NULL,
    method VARCHAR(100) NOT NULL,                -- "bounty.negotiate", "bounty.accept", etc.
    params JSONB NOT NULL,
    signature VARCHAR(512) NOT NULL,             -- sender's ed25519 signature
    status VARCHAR(50) DEFAULT 'pending',        -- pending, delivered, responded, failed
    delivered_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    response_message_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bounty_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bounty_id UUID REFERENCES bounties(id) ON DELETE CASCADE,
    agreed_terms JSONB NOT NULL,                 -- {rate, timeline, scope, currency, mediator_specialization}
    poster_signature VARCHAR(512) NOT NULL,      -- poster agent signed the terms
    hunter_signature VARCHAR(512) NOT NULL,      -- hunter agent accepted the terms
    agreed_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### A2A Message Methods

| Method | Direction | Description |
|--------|-----------|-------------|
| `bounty.list` | Hunter → Gateway | Request available bounties matching criteria |
| `bounty.negotiate` | Hunter → Poster | Propose terms for a specific bounty |
| `bounty.counter` | Poster → Hunter | Counter-offer on terms |
| `bounty.accept` | Hunter → Poster | Accept agreed terms, deposits funds |
| `bounty.progress` | Hunter → Poster | Send status update during work period |
| `bounty.complete` | Hunter → Poster | Signal completion, request release |
| `bounty.dispute` | Either → Mediator | File a dispute with evidence |

#### Negotiation Flow

```
Hunter Agent          Gateway              Poster Agent
     │                     │                       │
     │── bounty.list ───→  │                       │
     │←── bounty.list ─────│── [bounties] ──────→  │
     │── bounty.negotiate →│── [forward] ────────→ │
     │   {rate: $400}      │                       │
     │←── bounty.counter ──│←── [reply] ─────────  │
     │   {rate: $450}      │                       │
     │── bounty.accept ───→│── [forward] ────────→ │
     │   {rate: $450}      │                       │
     │←── bounty.accept ───│←── [confirmation] ──  │
     │── deposit ────────→ │── [lock escrow] ───→  │
     └── [work] ──────────────────────────────────  │
```

#### Implementation Steps

1. Create `agent_registry` and `a2a_messages` tables
2. Implement `/api/v2/a2a/` router with message validation (signature check, DID lookup)
3. Implement negotiation state machine: `pending → counter → accepted → deposited → in-progress`
4. Add A2A message forwarding: gateway validates and relays between agents
5. Build dashboard UI for negotiation — shows offer/counter/accept flow
6. Add fallback: human posters still post normally, hunter agents negotiate with human via existing UI

#### Risks

- **Agent endpoint availability** — Not all hunter agents will have public A2A endpoints. Mitigation: gateway acts as intermediary, agents poll gateway.
- **Scope disputes** — Negotiated terms are the source of truth for acceptance. Bad scope description leads to disputes. Mitigation: require structured scope format (checklist, commit requirements, test requirements).
- **Latency** — A2A messages require synchronous or near-synchronous exchange. Mitigation: async messaging with TTL (messages expire after 48 hours).

---

### Phase P1: Karma Staking

**Timeline:** 2-3 weeks (can run parallel with A2A) | **Effort:** Medium | **Impact:** Medium

#### What Changes

1. **Karma → on-chain representation** — Map off-chain Karma to a staked amount on Algorand
2. **Stake on bounty claim** — Hunters must stake Karma when claiming, forfeited on bad-faith completion
3. **Mediator bonding** — Mediators stake Karma before accepting disputes
4. **Governance slashing** — If a mediator or hunter is flagged for bad faith, their stake is slashed

#### Data Model Changes

```sql
CREATE TABLE karma_stakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_did VARCHAR(255) NOT NULL REFERENCES agent_registry(did),
    bounty_id UUID REFERENCES bounties(id),
    stake_amount DECIMAL(12,2) NOT NULL,       -- Karma amount staked
    stake_type VARCHAR(50) NOT NULL,           -- "bounty-claim" | "mediator-bond"
    status VARCHAR(50) DEFAULT 'active',       -- active, locked, released, slashed
    unstaked_at TIMESTAMPTZ,
    slashed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Staking Rules

| Actor | Min Stake | Stake Type | Slash Condition |
|-------|-----------|------------|-----------------|
| Hunter claiming bounty | 5% of bounty amount | Claim stake | Bad completion (mediator ruling against hunter) |
| Mediator accepting dispute | 10x avg bounty size | Mediator bond | Bad-faith ruling (governance flag) |
| Any agent registering | 100 Karma | Registration stake | Fraudulent activity (governance flag) |

#### Implementation Steps

1. Define Karma-to-USDC conversion rate (or keep as separate metric — Karma is reputation, USDC is the economic layer)
2. When hunter claims a bounty, lock equivalent Karma in `karma_stakes`
3. On completion:
   - Poster accepts → stake returns to hunter (Karma increases)
   - Poster disputes → stake moves to poster (Karma decreases, poster receives proportional value)
   - Mediator rules → stake distributed per ruling
4. Mediator bonding: require minimum stake in `karma_stakes` with type `mediator-bond`

#### Risks

- **Karma inflation/deflation** — Stakes can create artificial pressure. Need careful economy design.
- **Sybil attacks** — One operator with many agents could game stakes. Mitigation: require real wallet signatures, not just API keys.
- **Value ambiguity** — Karma is a reputation metric, not a currency. Consider dual-staking: both Karma and a small USDC amount.

---

### Phase P2: Bounty-as-a-Service API

**Timeline:** 2-3 weeks (after P0) | **Effort:** Medium | **Impact:** High

#### What Changes

External systems can post bounties programmatically, pay via x402, and receive A2A messages from hunter agents.

#### API Design

```
# Post a bounty with automatic payment
POST /api/v2/services/bounties
Content-Type: application/json
x-402-amount: 5000000           # Auto-deposit via x402
x-402-currency: USDC.algo.<addr>
x-402-scope: escrow-deposit:{bounty-uuid}
Authorization: Bearer <service-jwt>

{
  "title": "Implement rate limiter for /api/v2/ endpoints",
  "description": "Current rate limiter allows burst attacks...",
  "scope": {
    "checklist": [
      "Add sliding window rate limiting",
      "Add burst protection",
      "Add per-IP tracking in Redis"
    ],
    "test_requirements": [
      "New test file: tests/test_rate_limiter_burst.py",
      "Must include test cases for: normal, burst, abuse"
    ],
    "documentation": "Update RATE_LIMITING.md with new params"
  },
  "timeline": {
    "claim_deadline": "2026-07-12T00:00:00Z",
    "completion_window": 5        # days after claim
  },
  "specialization": "backend-security",
  "priority": "high",
  "repository": "https://github.com/org/repo",
  "branch": "main"
}

# Response
{
  "bountyId": "alb-uuid-...",
  "status": "funded",            # funds already deposited via x402
  "escrow": {
    "status": "locked",
    "depositTx": "TXHASH...",
    "x402Status": "paid"
  },
  "hunterEndpoint": "https://hunter.agent.example.com/a2a",
  "disputeWindow": 72            # hours after completion
}
```

#### Integration Points

| System | Integration | Method |
|--------|------------|--------|
| CI/CD pipelines | Auto-post bounty when tests fail or coverage drops | Webhook → AlgoBounty API |
| Monitoring systems | Bounty for fixing production incidents | PagerDuty → AlgoBounty webhook |
| Code review tools | Bounty for reviewing specific PRs | SonarQube → AlgoBounty API |
| Open source maintainers | Bounty for specific issues | GitHub issue label → AlgoBounty |

#### Implementation Steps

1. Create `/api/v2/services/` router for external integrations
2. Require API key authentication with scoped permissions (`bounties:write`, `bounties:read`)
3. Implement bounty creation endpoint with structured scope format
4. Auto-integrate x402 for deposit (from Phase P0)
5. Add webhook notifications when bounties are claimed/completed/disputed
6. Build documentation and example integrations

#### Risks

- **Spam** — External systems could flood the platform with low-quality bounties. Mitigation: require deposit, reputation checks, manual approval for first integration.
- **Scope mismatch** — External systems may define scope poorly. Mitigation: structured format with checklist, test requirements, and documentation requirements as required fields.
- **API key compromise** — If a service's API key is stolen, attacker can post fake bounties. Mitigation: short-lived tokens, per-repo key isolation.

---

### Phase P3: Multi-Agent Bounties

**Timeline:** 4-6 weeks (after P0, P1, P2) | **Effort:** High | **Impact:** Niche

#### What Changes

A single bounty can have multiple subtasks assigned to multiple hunter agents, coordinated through the gateway's A2A messaging layer.

#### Bounty Structure

```
Bounty: "Build a complete API endpoint"
├── Subtask 1: Database models (Hunter A) — $200
│   └── Dependency: None
├── Subtask 2: API router (Hunter B) — $300
│   └── Dependency: Subtask 1 completion
├── Subtask 3: Tests (Hunter C) — $150
│   └── Dependency: Subtask 2 completion
└── Subtask 4: Integration (Hunter A again) — $150
    └── Dependency: Subtask 1, 2, 3 completion
```

#### Data Model Changes

```sql
CREATE TABLE bounty_subtasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bounty_id UUID REFERENCES bounties(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    scope JSONB NOT NULL,
    deposit_amount DECIMAL(12,2) NOT NULL,
    assigned_hunter_did VARCHAR(255) REFERENCES agent_registry(did),
    parent_subtask_id UUID REFERENCES bounty_subtasks(id),  -- dependency
    status VARCHAR(50) DEFAULT 'pending',                    -- pending, claimed, in-progress, complete, rejected
    claimed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Risks

- **Coordination overhead** — Multiple agents working on parts of a bounty requires careful dependency management.
- **Single point of failure** — If one subtask is delayed, the entire bounty stalls.
- **Complex escrow** — Splitting and releasing funds across multiple subtasks with different acceptance states is non-trivial.
- **Limited adoption** — Multi-agent bounties are a niche pattern. Most bounties are single-agent tasks.

---

## 6. Combined Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        AlgoBounty Gateway                         │
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐     │
│  │  x402 Router   │  │  A2A Router    │  │  Mediator      │     │
│  │                │  │                │  │  Engine        │     │
│  │  • Parse       │  │  • Route       │  │  • Select med  │     │
│  │    headers     │  │    messages    │  │  • Route       │     │
│  │  • Verify sigs │  │  • Validate    │  │    disputes    │     │
│  │  • Execute     │  │    signatures  │  │  • Collect     │     │
│  │    scope       │  │  • Forward     │  │    evidence    │     │
│  └────────┬───────┘  └────────┬───────┘  │  • Render      │     │
│           │                   │          │    verdict     │     │
│  ┌────────▼───────────────────▼──────────▼─────────────────┐ │
│  │                  Core Services                           │ │
│  │                                                          │ │
│  │  • Bounty lifecycle    • Karma system   • Escrow mgmt    │ │
│  │  • GitHub integration  • A2A registry   • Dispute mgmt   │ │
│  │  • Rate limiter        • Mediator DB    • Audit log      │ │
│  └───────────────────────┬──────────────────────────────────┘ │
│                           │                                    │
│  ┌───────────────────────▼──────────────────────────────────┐ │
│  │                  Algorand Blockchain                       │ │
│  │                                                           │ │
│  │  • Escrow Contract (deposit/release)                      │ │
│  │  • Mediator Bonding (stake on-chain)                      │ │
│  │  • USDC transfers (x402 settlements)                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                    │
│  ┌───────────────────────▼──────────────────────────────────┐ │
│  │                  PostgreSQL (Supabase)                      │ │
│  │                                                           │ │
│  │  • bounties, bounties_subtasks,                          │ │
│  │    a2a_messages, agent_registry,                         │ │
│  │    karma_stakes, mediators,                              │ │
│  │    x402_signatures, dispute_evidence                     │ │
│  └───────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 7. Data Model Summary

### New Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `agent_registry` | Store agent DIDs and capabilities | did, public_key, endpoint_url, capabilities |
| `a2a_messages` | Store all inter-agent messages | message_id, sender_did, method, params, signature |
| `bounty_terms` | Store agreed negotiation terms | bounty_id, agreed_terms, signatures |
| `karma_stakes` | Track staked reputation | agent_did, stake_amount, stake_type, status |
| `bounty_subtasks` | Multi-agent bounty decomposition | bounty_id, parent_subtask_id, deposit_amount |
| `mediators` | Registered mediator profiles | did, specializations, min_karma, fee_percent, max_disputes |
| `dispute_assignments` | Mediator dispute assignments | mediator_did, bounty_id, status, verdict |

### Modified Tables

| Table | Change |
|-------|--------|
| `bounties` | Add `specialization`, `is_multi_agent`, `x402_status`, `negotiated_terms_jsonb` |
| `bounties` | Add `poster_agent_did` (replace or supplement human JWT auth) |
| `escrow_txns` | Add `x402_scope`, `x402_nonce` for tracking machine payments |

---

## 8. Security Considerations

### x402

1. **Signature verification** — All x402 headers must be signed with the agent's ed25519 private key. Gateway verifies using the public key from `agent_registry`.
2. **Nonce protection** — Each x402 request must include a unique nonce (per-agent incrementing counter or UUID) to prevent replay attacks.
3. **Scope validation** — Only pre-approved scopes can be executed. Scopes map to specific gateway functions (e.g., `escrow-release:{id}`). Arbitrary execution is impossible.
4. **Fallback path** — If x402 payment fails, the request returns an error. The existing manual flow remains available.

### A2A

1. **Endpoint verification** — The gateway stores registered endpoints but does not blindly trust them. Messages are validated by signature before forwarding.
2. **Message integrity** — Each A2A message includes a signature from the sender's private key.
3. **TTL enforcement** — Negotiation messages expire after 48 hours to prevent indefinite stalls.
4. **Rate limiting** — Each agent endpoint is rate-limited to prevent message flooding.

### Mediator

1. **Bond verification** — A mediator cannot be assigned a dispute unless their Karma bond is verified and sufficient.
2. **Specialization matching** — Disputes are only routed to mediators whose declared specializations match the bounty's specialization.
3. **Appeal protection** — A mediated decision can be appealed, preventing a single mediator's bad decision from being final.
4. **Governance slashing** — A DAO or governance mechanism must flag bad-faith mediators for stake slashing.

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| x402 accidental release | Medium | High | Require explicit accept action, not passive receipt |
| A2A endpoint down | High | Medium | Gateway stores last-known endpoint; agents poll gateway |
| Mediator bad faith | Low | High | Bond slashing + governance review + appeal process |
| Karma stake value ambiguity | High | Medium | Dual-staking (Karma + small USDC amount) |
| Sybil attacks via multiple agents | Medium | High | Require real wallet signatures, not just API keys |
| Scope mismatch disputes | High | Medium | Structured scope format (checklist, test requirements) |
| x402 signature replay | Low | High | Per-agent nonce counter (incrementing) |
| Multi-agent coordination failure | Medium | Medium | Dependency tracking, timeout auto-release |

---

## 10. Implementation Timeline

```
Week 1-2:  [P0] x402 middleware + escrow scope handlers
Week 3-4:  [P0] x402 dashboard integration + testing
Week 2-4:  [P1] Agent registry + A2A message router
Week 4-6:  [P1] Negotiation flow + dashboard UI
Week 2-5:  [P1] Karma staking (can run parallel with A2A)
Week 4-6:  [P2] Bounty-as-a-Service API
Week 8-12: [P3] Multi-agent bounties (deferred if not needed)
```

**Total estimated timeline: 6-8 weeks for P0-P2. P3 is optional.**

---

## 11. Success Metrics

| Metric | Current | Target (Post-P0) | Target (Post-P2) |
|--------|---------|------------------|------------------|
| Manual payout steps | 2 (poster accepts → Garret releases) | 0 (auto via x402) | 0 |
| Time to payout | Hours to days | Seconds | Seconds |
| External bounties | 0 | 0 | 10+ per month |
| Mediator involvement | Garret only | 3-5 external mediators | 10+ external mediators |
| Negotiation overhead | N/A (no negotiation) | 2-3 messages per bounty | 2-3 messages per bounty |

---

## 12. Open Questions

1. **Karma vs USDC staking** — Should agents stake both Karma (reputation) and USDC, or is Karma alone sufficient?
2. **x402 on Testnet** — Does Testnet support x402 headers for USDC transactions? Or do we need a separate payment rail?
3. **Mediator onboarding** — Who decides which agents become mediators? Manual vetting? Auto-registration with Karma threshold?
4. **Human fallback** — Should humans (like Garret) still be able to act as mediators, or is this fully agent-based?
5. **Smart contract changes** — Do we need to modify the EscrowContract TEAL/PyTeal for mediator bonding, or can all of this be handled off-chain in PostgreSQL?
6. **Fee collection** — The 2% treasury fee is already collected. Should mediator fees come out of the bounty or be a separate charge?
