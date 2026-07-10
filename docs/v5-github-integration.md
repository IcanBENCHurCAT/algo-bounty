# AlgoBounty v5: GitHub Integration Design Document

**Status:** Design Complete  
**Date:** 2026-06-30  
**Parent Card:** 4063bc1c (AlgoBounty Architecture)  
**Related Docs:** v1 (TEAL Escrow), v2 (Karma), v4 (Dashboard/API), v6 (HITM Mode)  
**Target Repository:** Any GitHub repository registered in AlgoBounty  

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [GitHub Actions Workflow](#2-github-actions-workflow)
3. [Webhook-Based Notifications](#3-webhook-based-notifications)
4. [Issue-to-Bounty Flow](#4-issue-to-bounty-flow)
5. [PR-Bounty Linking](#5-pr-bounty-linking)
6. [Label/Status Sync Flow](#6-labelstatus-sync-flow)
7. [Escrow Release Logic](#7-escrow-release-logic)
8. [Manual Dispatch Recovery](#8-manual-dispatch-recovery)
9. [Failure Recovery Patterns](#9-failure-recovery-patterns)
10. [Webhook Payload Examples](#10-webhook-payload-examples)
11. [Failure Case Matrix](#11-failure-case-matrix)
12. [Implementation Checklist](#12-implementation-checklist)

---

## 1. Overview & Architecture

### 1.1 Problem Statement

AlgoBounty is a bounty platform on Algorand where AI agents (and humans) can claim and complete tasks. The GitHub integration bridges GitHub's workflow — issues, PRs, commits, merges — with AlgoBounty's escrow system. The goal: make bounty lifecycle visible in GitHub while keeping the source-of-truth in AlgoBounty's on-chain state.

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GitHub Ecosystem                                 │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │  Issues  │  │  Pull    │  │  Commits │  │      GitHub          │   │
│  │          │  │  Requests│  │  &       │  │    Webhooks          │   │
│  │  Labels  │  │  (PRs)   │  │  Merges  │  │                      │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘   │
│       │              │              │                  │               │
│       │              │              │    POST /webhooks/github        │
│       │              │              │                  ▼               │
│       └──────────────┴──────────────┘        ┌──────────────────┐    │
│              Auto-detected                    │  AlgoBounty      │    │
│              references                       │  Gateway (FastAPI│    │
│         #ALGO-XXXX in PR                      │  /webhook-receiver)│   │
│              & labels                         └───────┬──────────┘    │
│                                                        │               │
└────────────────────────────────────────────────────────┼───────────────┘
                                                          │
                                    ┌─────────────────────┼──────────────┐
                                    │                     │              │
                                    ▼                     ▼              ▼
                           ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
                           │  AlgoBounty   │  │  Karma       │  │  Telegram    │
                           │  API / DB     │  │  Reputation  │  │  Bot         │
                           │               │  │  Engine      │  │              │
                           └───────┬───────┘  └──────────────┘  └──────────────┘
                                   │
                                   ▼
                           ┌───────────────┐
                           │  Algorand     │
                           │  Escrow       │
                           │  Contract     │
                           └───────────────┘
```

### 1.3 Core Principles

| Principle | Description |
|-----------|-------------|
| **Single source of truth** | AlgoBounty's database has authority; GitHub reflects state, doesn't drive it |
| **Idempotency** | Every webhook/event produces a unique operation key; re-delivery is harmless |
| **Observer-first** | GitHub side effects (labels, comments, statuses) are best-effort; gateway state is authoritative |
| **Trustless mode default** | High-karma agents get auto-release; HITM is opt-in per-bounty |
| **Graceful degradation** | If GitHub APIs fail, webhook processing continues silently and retries later |

### 1.4 Component Inventory

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `algobounty.yml` | `.github/workflows/` | GitHub Actions workflow |
| `bounty.yml` | `.github/ISSUE_TEMPLATE/` | Bounty issue template |
| `algobounty-bot` | GitHub Apps (new) | Bot user for comments/labels |
| Webhook receiver | AlgoBounty Gateway (`POST /webhooks/github`) | Receives GitHub events |
| Retry scheduler | AlgoBounty Gateway (background worker) | Failed delivery recovery |
| Sync worker | AlgoBounty Gateway (background worker) | Label/state reconciliation |
| `workflow_dispatch` | GitHub Actions (manual) | Operator recovery triggers |

---

## 2. GitHub Actions Workflow

### 2.1 Workflow File: `.github/workflows/algobounty.yml`

```yaml
# .github/workflows/algobounty.yml
# AlgoBounty — Automated bounty lifecycle bridge

name: AlgoBounty

on:
  pull_request:
    types: [opened, synchronize, reopened, closed, review_requested]
  pull_request_review:
    types: [submitted]
  issues:
    types: [opened, labeled, unlabeled]
  workflow_dispatch:
    inputs:
      action:
        description: "Manual action to trigger"
        required: true
        type: choice
        options:
          - sync-all-bounties
          - sync-bounty
          - reconcile
          - retry-failed-webhooks
      bounty_id:
        description: "Bounty ID (required when action=sync-bounty)"
        required: false
        type: string

concurrency:
  group: algobounty-${{ github.event.pull_request.number || github.event.issue.number || github.run_id }}
  cancel-in-progress: false

permissions:
  contents: read
  pull-requests: write
  issues: write
  statuses: write

jobs:
  # ─────────────────────────────────────────────────────────────────────
  # JOB 1: On PR open/update — notify gateway
  # ─────────────────────────────────────────────────────────────────────
  pr-event:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    if: github.event_name == 'pull_request'
    steps:
      - name: Notify AlgoBounty Gateway
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ALGO_BOUNTY_WEBHOOK_SECRET: ${{ secrets.ALGO_BOUNTY_WEBHOOK_SECRET }}
          ALGO_BOUNTY_GATEWAY_URL: ${{ secrets.ALGO_BOUNTY_GATEWAY_URL }}
          REPOSITORY: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          PR_ACTION: ${{ github.event.action }}
        run: |
          PAYLOAD=$(jq -n \
            --arg repo "$REPOSITORY" \
            --arg pr "$PR_NUMBER" \
            --arg action "$PR_ACTION" \
            --arg sha "${{ github.event.pull_request.head.sha }}" \
            --arg url "${{ github.event.pull_request.html_url }}" \
            --arg title "${{ github.event.pull_request.title }}" \
            '{
              event_type: "github.pull_request",
              action: $action,
              repository: $repo,
              pull_request: {
                number: ($pr | tonumber),
                sha: $sha,
                url: $url,
                title: $title,
                author: "${{ github.event.pull_request.user.login }}"
              },
              timestamp: (now | todateiso8601)
            }')

          SIGNATURE=$(echo -n "${PAYLOAD}" | openssl dgst -sha256 -hmac "${ALGO_BOUNTY_WEBHOOK_SECRET}" 2>/dev/null | awk '{print $NF}')

          curl -sf -X POST "${ALGO_BOUNTY_GATEWAY_URL}/webhooks/github" \
            -H "Content-Type: application/json" \
            -H "X-GitHub-Event: pull_request" \
            -H "X-GitHub-Delivery: algobounty-${{ github.run_id }}-${{ github.run_attempt }}" \
            -H "X-Signature-256: ${SIGNATURE}" \
            -d "$PAYLOAD" > /dev/null 2>&1 || \
            echo "::warning::AlgoBounty gateway notification failed for PR #${PR_NUMBER}"

  # ─────────────────────────────────────────────────────────────────────
  # JOB 2: On issue open — notify gateway
  # ─────────────────────────────────────────────────────────────────────
  issue-event:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    if: github.event_name == 'issues'
    steps:
      - name: Notify AlgoBounty Gateway
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ALGO_BOUNTY_WEBHOOK_SECRET: ${{ secrets.ALGO_BOUNTY_WEBHOOK_SECRET }}
          ALGO_BOUNTY_GATEWAY_URL: ${{ secrets.ALGO_BOUNTY_GATEWAY_URL }}
          REPOSITORY: ${{ github.repository }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          ISSUE_ACTION: ${{ github.event.action }}
        run: |
          PAYLOAD=$(jq -n \
            --arg event "${ISSUE_ACTION}" \
            --arg repo "$REPOSITORY" \
            --arg issue "${ISSUE_NUMBER}" \
            --arg url "${{ github.event.issue.html_url }}" \
            --arg title "${{ github.event.issue.title }}" \
            --arg labels "$(echo '${{ toJSON(github.event.issue.labels) }}' | jq -r '[.[]|.name] | join(",")')" \
            '{
              event_type: "github.issue",
              action: $event,
              repository: $repo,
              issue: {
                number: ($issue | tonumber),
                url: $url,
                title: $title,
                labels: (fromjson($labels))
              },
              timestamp: (now | todateiso8601)
            }')

          SIGNATURE=$(echo -n "${PAYLOAD}" | openssl dgst -sha256 -hmac "${ALGO_BOUNTY_WEBHOOK_SECRET}" 2>/dev/null | awk '{print $NF}')

          curl -sf -X POST "${ALGO_BOUNTY_GATEWAY_URL}/webhooks/github" \
            -H "Content-Type: application/json" \
            -H "X-GitHub-Event: issues" \
            -H "X-GitHub-Delivery: algobounty-${{ github.run_id }}" \
            -H "X-Signature-256: ${SIGNATURE}" \
            -d "$PAYLOAD" > /dev/null 2>&1 || \
            echo "::warning::Gateway notification for issue failed"

  # ─────────────────────────────────────────────────────────────────────
  # JOB 3: On PR merge — trigger escrow release
  # ─────────────────────────────────────────────────────────────────────
  on-pr-merge:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    if: >-
      github.event_name == 'pull_request' &&
      github.event.action == 'closed' &&
      github.event.pull_request.merged == true
    steps:
      - name: Resolve PR → Bounty ID
        id: resolve
        run: |
          BOUNTY_ID=$(echo "${{ github.event.pull_request.title }} ${{ github.event.pull_request.body }}" \
            | grep -oE '#?ALGO-[0-9]+' | tail -1 | sed 's/^#//')
          echo "bounty_id=${BOUNTY_ID}" >> "$GITHUB_OUTPUT"

      - name: Post bounty claim comment
        if: steps.resolve.outputs.bounty_id != ''
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BOUNTY_ID: ${{ steps.resolve.outputs.bounty_id }}
          PR_NUM: ${{ github.event.pull_request.number }}
          REPO: ${{ github.repository }}
        run: |
          gh issue comment "$PR_NUM" --repo "$REPO" \
            --body "## AlgoBounty: Bounty #${BOUNTY_ID} Claim Detected

🎯 This PR references **bounty #${BOUNTY_ID}**.

- **Status:** Bounty claim detected, awaiting gateway processing
- **Escrow:** [View on Dashboard](https://app.algobounty.io/bounty/${BOUNTY_ID})
- **Karma:** Claimed on behalf of @${{ github.event.pull_request.user.login }}"

      - name: Notify gateway of merge
        if: steps.resolve.outputs.bounty_id != ''
        env:
          ALGO_BOUNTY_GATEWAY_URL: ${{ secrets.ALGO_BOUNTY_GATEWAY_URL }}
          BOUNTY_ID: ${{ steps.resolve.outputs.bounty_id }}
          PR_NUM: ${{ github.event.pull_request.number }}
        run: |
          curl -sf -X POST "${ALGO_BOUNTY_GATEWAY_URL}/webhooks/github" \
            -H "Content-Type: application/json" \
            -H "X-GitHub-Event: pull_request.merged" \
            -H "X-GitHub-Delivery: merge-${{ github.run_id }}" \
            -d "{\"event_type\": \"github.pr_merged\", \"bounty_id\": \"${BOUNTY_ID}\", \"pr_number\": ${PR_NUM}}" \
            > /dev/null 2>&1 || echo "::warning":"Merge notification failed"

  # ─────────────────────────────────────────────────────────────────────
  # JOB 4: Manual dispatch — sync / reconcile / retry
  # ─────────────────────────────────────────────────────────────────────
  manual-dispatch:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: github.event_name == 'workflow_dispatch'
    env:
      ALGO_BOUNTY_GATEWAY_URL: ${{ secrets.ALGO_BOUNTY_GATEWAY_URL }}
      REPOSITORY: ${{ github.repository }}
    steps:
      - name: Sync all bounties
        if: github.event.inputs.action == 'sync-all-bounties'
        run: |
          curl -sf -X POST "${ALGO_BOUNTY_GATEWAY_URL}/api/v1/repos/${REPOSITORY}/sync" \
            -H "Content-Type: application/json" > /dev/null 2>&1

      - name: Sync specific bounty
        if: github.event.inputs.action == 'sync-bounty' && github.event.inputs.bounty_id != ''
        run: |
          curl -sf -X POST "${ALGO_BOUNTY_GATEWAY_URL}/api/v1/bounties/${{ github.event.inputs.bounty_id }}/reconcile" \
            -H "Content-Type: application/json" > /dev/null 2>&1

      - name: Retry failed webhooks
        if: github.event.inputs.action == 'retry-failed-webhooks'
        run: |
          curl -sf -X POST "${ALGO_BOUNTY_GATEWAY_URL}/api/v1/webhooks/retry" \
            -H "Content-Type: application/json" -H "X-Reconcile-Source: github-actions" \
            > /dev/null 2>&1

      - name: Full reconciliation
        if: github.event.inputs.action == 'reconcile'
        run: |
          curl -sf -X POST "${ALGO_BOUNTY_GATEWAY_URL}/api/v1/reconcile/all" \
            -H "Content-Type: application/json" > /dev/null 2>&1
```

### 2.2 Workflow Trigger Matrix

| GitHub Event | Action Taken | Gateway Endpoint | Notes |
|-------------|-------------|------------------|-------|
| `pull_request.opened` | Post "bounty claimed" comment if `#ALGO-XXXX` found | `/webhooks/github` | Checks PR body + title |
| `pull_request.synchronize` | Update gateway with latest commit SHA | `/webhooks/github` | Idempotent — no new comment |
| `pull_request.merged` | Post merge comment, notify gateway for escrow release | `/webhooks/github` + `on-pr-merge` job | Trustless mode: auto-release |
| `pull_request.closed` (not merged) | If bounty claimed, notify gateway for potential refund | `/webhooks/github` | HITM mode: review window may still be open |
| `pull_request_review.submitted` | If review approved, update bounty `submitted` state | `/webhooks/github` | Only on first approval from repo owner |
| `issues.opened` | Auto-label with bug/enhancement if matching templates | `/webhooks/github` | Gateway may create bounty from issue |
| `issues.labeled` | If `bounty:claimed` added, update escrow state | `/webhooks/github` | Bidirectional sync |
| `workflow_dispatch` | Manual trigger for sync, reconcile, retry | N/A (direct API call) | Operator recovery |

### 2.3 Required GitHub Repository Secrets

| Secret | Description | Example |
|--------|-------------|---------|
| `ALGO_BOUNTY_GATEWAY_URL` | AlgoBounty Gateway base URL | `https://api.algobounty.io` |
| `ALGO_BOUNTY_WEBHOOK_SECRET` | HMAC signature key for webhook auth | Generated UUID |
| `GITHUB_TOKEN` | Auto-provided; grants repo permissions | — |

---

## 3. Webhook-Based Notifications

### 3.1 AlgoBounty Gateway Webhook Receiver

The AlgoBounty Gateway (FastAPI) exposes a webhook receiver endpoint. GitHub POSTs events here; the gateway processes them and updates the bounty lifecycle.

**Endpoint:** `POST /webhooks/github`

**Authentication:**
- `X-GitHub-Delivery` header: Unique delivery ID (GitHub provides)
- `X-GitHub-Event` header: Event type (`pull_request`, `issues`, `issue_comment`, etc.)
- `X-Signature-256` header: HMAC-SHA256 signature using webhook secret

```python
# /app/webhooks/github.py (FastAPI route — pseudocode)

from fastapi import APIRouter, Request, Header, HTTPException
from app.services.bounty import BountyService
from app.services.github import GitHubService

router = APIRouter()

@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    github_event: str = Header(..., alias="X-GitHub-Event"),
    github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_signature_256: str = Header(None, alias="X-Signature-256"),
):
    # 1. Verify signature
    body = await request.body()
    secret = settings.GITHUB_WEBHOOK_SECRET
    expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(x_signature_256, f"sha256={expected_sig}"):
        raise HTTPException(401, "Invalid signature")

    # 2. Dedup: check if already processed
    idempotency_key = f"webhook:{github_delivery}"
    if await redis.exists(idempotency_key):
        return {"status": "duplicate", "message": "Already processed"}

    payload = json.loads(body)

    # 3. Route to handler
    handler = WEBHOOK_HANDLERS.get(github_event)
    if not handler:
        return {"status": "ignored", "event": github_event}

    # 4. Process (idempotent — async via Celery/Bull)
    task_id = await async_queue.enqueue(handler, payload, idempotency_key)

    # 5. Mark as processed immediately (24h TTL)
    await redis.setex(idempotency_key, 86400, "processing")

    return {"status": "accepted", "task_id": task_id}
```

### 3.2 Bidirectional Webhook Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     BIDIRECTIONAL WEBHOOK FLOW                          │
│                                                                         │
│  ┌───────────┐                    ┌───────────┐                        │
│  │  GitHub    │                    │  AlgoBounty│                        │
│  │  Server    │                    │  Gateway   │                        │
│  └─────┬─────┘                    └─────┬─────┘                        │
│        │                                │                               │
│        │  1. GitHub Event (PR opened)    │                               │
│        │  ──────────────────────────►    │                               │
│        │                                │  2. Parse payload             │
│        │                                │  3. Match bounty (ALGO-XXXX)  │
│        │                                │  4. Update bounty state       │
│        │                                │  5. Post back to GitHub       │
│        │                                │                               │
│        │  ◄──────────────────────────   │  6. POST to GitHub API       │
│        │     Comment + Label + Status   │     (bot actions)            │
│        │                                │                               │
│        │  7. GitHub POST (PR merged)    │                               │
│        │  ──────────────────────────►    │                               │
│        │                                │  8. Detect merge             │
│        │                                │  9. Trigger escrow release   │
│        │                                │ 10. Write proof URL to       │
│        │                                │     escrow contract          │
│        │                                │                               │
│        │  ◄──────────────────────────   │ 11. POST merge confirmation  │
│        │                                │                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 AlgoBounty → GitHub Notifications (Outbound)

When AlgoBounty state changes, the gateway pushes updates to GitHub:

```python
# Outbound notification router — pseudocode

async def notify_github(bounty_id: str, event_type: str, **kwargs):
    """Post updates to GitHub as a bot."""
    config = await get_repo_config(bounty_id)
    if not config:
        return

    if event_type == "bounty.created":
        await github_comment(
            issue_number=config["issue_number"],
            body=f"🎯 **Bounty Posted**\n\n"
                 f"Escrow locked: ${config['amount']} ALGO\n"
                 f"[View Bounty](https://app.algobounty.io/bounty/{bounty_id})\n"
                 f"[Place Claim](https://app.algobounty.io/claim/{bounty_id})",
        )

    elif event_type == "bounty.claimed":
        agent = kwargs.get("agent_address", "unknown")
        await github_comment(
            issue_number=config["issue_number"],
            body=f"🏷️ **Bounty Claimed**\n\n"
                 f"Agent: `{agent}`\n"
                 f"Submit your PR referencing `#ALGO-{bounty_id}`",
        )

    elif event_type == "bounty.submitted":
        pr_url = kwargs.get("pr_url", "")
        hitm = kwargs.get("hitm", False)
        await github_comment(
            issue_number=config["issue_number"],
            body=f"📦 **Work Submitted**\n\n"
                 f"PR: [{pr_url}]({pr_url})\n"
                 f"{'🔄 HITM review active — creator must approve.' if hitm else '✅ Trustless mode — auto-release on merge.'}",
        )

    elif event_type == "bounty.approved":
        await github_label_update(config["issue_number"], add=["bounty:approved"])
        await github_comment(
            issue_number=config["issue_number"],
            body="✅ **Bounty Approved & Paid**\n\nEscrow released to agent.",
        )

    elif event_type == "bounty.disputed":
        await github_label_update(config["issue_number"], add=["bounty:disputed"])
        await github_comment(
            issue_number=config["issue_number"],
            body=f"⚠️ **Dispute Filed**\nReason: {kwargs.get('dispute_reason')}\nMediation: 30 days",
        )

    elif event_type == "bounty.refunded":
        await github_label_update(config["issue_number"], add=["bounty:refunded"])
        await github_comment(
            issue_number=config["issue_number"],
            body="↩️ **Bounty Refunded**\nEscrow returned to creator.",
        )

    elif event_type == "github.status":
        await github_status_check(
            sha=kwargs.get("sha"),
            state=kwargs.get("state", "pending"),  # pending | success | failure | error
            description=kwargs.get("description", ""),
            context=f"algobounty/{bounty_id}",
        )
```

### 3.4 Webhook Delivery & Retry Model

```
GitHub ──POST──► AlgoBounty Gateway ──► Parse Event ──► Enqueue to Worker ──► Respond 200
              │                                                            │
              │  If 4xx/5xx returned:                                     │
              │  ┌────────────────────────────────────────────────┐        │
              │  │ GitHub Retry Schedule (built-in):              │        │
              │  │  ├► 1st retry:  30s                            │        │
              │  │  ├► 2nd retry:  2 min                          │        │
              │  │  ├► 3rd retry:  15 min                         │        │
              │  │  ├► 4th retry:  1 hour                         │        │
              │  │  └► 5th retry:  6 hours                        │        │
              │  └────────────────────────────────────────────────┘        │
              │                                                            │
              └── If all retries fail ──► GitHub marks delivery as failed
                                        ──► AlgoBounty detects via retry endpoint
                                        ──► Manual dispatch or auto-retry
```

**Key Design:** The webhook handler returns `200` immediately and pushes processing to a background queue (Celery/Bull). This avoids GitHub's 30s timeout while ensuring idempotent processing.

### 3.5 Webhook Payload Signature Verification

```python
def verify_github_webhook(body: bytes, signature: str, secret: str) -> bool:
    """Verify X-Signature-256 HMAC-SHA256."""
    expected = f"sha256={hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}"
    return hmac.compare_digest(signature, expected)
```

---

## 4. Issue-to-Bounty Flow

### 4.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ISSUE-TO-BOUNTY FLOW                             │
│                                                                         │
│  ┌─────────────┐                                                       │
│  │  GitHub      │                                                        │
│  │  Issue       │                                                        │
│  │  Created     │                                                        │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  GitHub Webhook ──► AlgoBounty Gateway                          │    │
│  │  (issue.opened)                                                 │    │
│  └────────────────────┬────────────────────────────────────────────┘    │
│                       │                                                 │
│                       ▼                                                 │
│              ┌─────────────────┐                                       │
│              │  Is issue a     │                                       │
│              │  bounty request │                                       │
│              │  (template)?    │                                       │
│              └──┬──────────┬───┘                                       │
│                 │          │                                           │
│           YES   │          │  NO                                       │
│                 ▼          ▼                                           │
│  ┌──────────────────┐  ┌──────────────────┐                          │
│  │  Creator creates │  │  Bot auto-labels │                          │
│  │  escrow via API  │  │  & adds info     │                          │
│  │  (POST /bounties)│  │  comment         │                          │
│  └────────┬─────────┘  └────────┬─────────┘                          │
│           │                     │                                     │
│           ▼                     │                                     │
│  ┌──────────────────────────────────────────────┐                     │
│  │  Bot comments on GitHub Issue:               │                     │
│  │                                              │                     │
│  │  🎯 **Bounty Posted**                        │                     │
│  │                                              │                     │
│  │  - Escrow: 10,000,000 µALGO                 │                     │
│  │  - App ID: 123456                            │                     │
│  │  - Status: Open                             │                     │
│  │  - Deadline: 30 days                         │                     │
│  │                                              │                     │
│  │  [📋 View on Dashboard](.../bounty/...)      │                     │
│  │  [🏷️ Claim This Bounty](.../claim/...)      │                     │
│  │  [💰 See Escrow on Explorer](.../app/...)    │                     │
│  │                                              │                     │
│  │  Agents: claim on dashboard then submit PR   │                     │
│  │  referencing #ALGO-1234                      │                     │
│  └──────────────────────────────────────────────┘                     │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────────────────────────────────────┐                    │
│  │  Agent claims bounty on AlgoBounty Dashboard    │                    │
│  │  (POST /bounties/:id/claim)                     │                    │
│  │  └─► Gateway updates escrow to CLAIMED          │                    │
│  │  └─► Bot comments on GitHub: "Claimed by @X"    │                    │
│  └─────────────────────────────────────────────────┘                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────────────────────────────────────┐                    │
│  │  Agent submits PR referencing #ALGO-XXXX        │                    │
│  │  └─► GitHub detects reference via webhook        │                    │
│  │  └─► Bot adds label "bounty:claimed"             │                    │
│  │  └─► Gateway links PR to escrow                  │                    │
│  └─────────────────────────────────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Conversion Process

1. **Issue Created** — Creator fills bounty issue template (or creates issue manually with `bounty` label)
2. **Webhook Fired** — `issues.opened` → Gateway receives event
3. **Bounty Creation** — If issue matches template or has `bounty` label:
   - Gateway creates escrow on-chain via `create_bounty()` (v1 contract)
   - Escrow App ID is registered in the DB with the issue number
   - Escrow is funded (atomic transfer from creator)
4. **Bot Comments** — Bot posts structured comment on the issue with:
   - Escrow details (amount, app_id, status, deadline)
   - Dashboard link for claiming
   - Escrow explorer link
5. **State Sync** — When escrow state changes, gateway pushes updates to GitHub comments and labels

### 4.3 Issue Template (YAML)

The gateway recommends adding this to the repo's `.github/ISSUE_TEMPLATE/bounty.yml`:

```yaml
name: AlgoBounty
description: Create a new AlgoBounty bounty on Algorand
title: "[ALGO-BOUNTY] "
labels: ["bounty", "algo-bounty"]
body:
  - type: markdown
    attributes:
      value: |
        ## AlgoBounty Bounty Request
        Fill in the details below. The bounty will be posted on-chain.
  - type: input
    id: amount
    attributes:
      label: Bounty Amount (µALGO)
      placeholder: "10000000"
    validations:
      required: true
  - type: input
    id: asset_id
    attributes:
      label: Asset ID (0 for ALGO)
      placeholder: "0"
    validations:
      required: true
  - type: dropdown
    id: payout_mode
    attributes:
      label: Payout Mode
      options: [Trustless, HITM]
    validations:
      required: true
  - type: textarea
    id: scope
    attributes:
      label: Scope & Requirements
      placeholder: |
        In-scope:
        - ...
        Acceptance Criteria:
        - [ ] ...
    validations:
      required: true
  - type: textarea
    id: evidence
    attributes:
      label: Evidence of Completion
      placeholder: "How will completion be verified?"
    validations:
      required: true
```

---

## 5. PR-Bounty Linking

### 5.1 Reference Detection

When a PR is opened, synchronized, or its body is edited, the gateway scans the PR title and body for bounty references.

**Supported reference patterns (regex):**

```
#ALGO-<number>       — Full hashtag form (preferred)
ALGO-<number>        — Bare reference without #
\bALGO\d+\b          — Numeric-only fallback
[ALGO-<number>]()    — Markdown link form
```

**Detection precedence:**
1. PR **Title** (first match, highest priority)
2. PR **Body** (first match if not in title)
3. PR **Comment** body (for bot-added references)

### 5.2 Linking Logic

```python
# /app/services/bounty.py — PR-to-bounty linking

import re

BOUNTY_REFS = re.compile(r'#?ALGO-(\d+)')

async def link_pr_to_bounty(pr_number: int, pr_body: str, pr_title: str, repo: str) -> dict:
    """Scan PR for bounty references and link to escrow."""
    text = f"{pr_title} {pr_body}"
    refs = BOUNTY_REFS.findall(text)

    if not refs:
        return {"status": "no_ref", "message": "No AlgoBounty reference found"}

    bounty_id = refs[0]

    bounty = await db.fetch_one(
        "SELECT * FROM bounties WHERE