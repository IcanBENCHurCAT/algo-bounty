---
name: "proxy-user-experience"
description: "Drives Playwright to run simulated user personas through key application flows, captures screenshots/timings/monologues, and generates visual HTML and engineering specs reports."
---

# Proxy User Experience (Playwright Simulator)

This skill drives **Playwright** to simulate real users (defined by personas from `algo-bounty-user-experience`) interacting with the AlgoBounty application. It tracks timing, handles wallets via mock signatures, captures step-by-step screenshots, and coordinates with the UX researcher to produce findings.

---

## 1. Skill Dependencies

This skill integrates and depends on two sibling skills. **Always load these first before executing**:
- [algo-bounty-style](../algo-bounty-style/SKILL.md) — The living design system and design tokens guide.
- [algo-bounty-user-experience](../algo-bounty-user-experience/SKILL.md) — The UX researcher and persona generator engine.

---

## 2. Multi-Actor Wallet Integration

To support flows like creation, claiming, and voting, the simulator uses deterministic wallets derived via `scripts/wallet-factory.py`.

### 2.1 Wallet Setup Rules
1. **Never use real mnemonic phrases** or mainnet accounts.
2. Ensure the gateway is running in **sandbox/local mode** (`ALGORAND_NETWORK=sandbox`).
3. For endpoints requiring a `signed_txn` (like `/claim` or `/approve`), compile the mock transactions with the actor's deterministic credentials or omit them if sandbox bypass is active.
4. Set the authentication headers using JWTs obtained via `python scripts/wallet-factory.py --auth <gateway_url>`.

### 2.2 Actor Wallet Registry
- **`CREATOR`**: The user who posts bounties.
- **`WORKER`**: The user claiming and submitting work.
- **`WORKER_2`**: Second worker for collision/abandonment scenarios.
- **`ARBITRATOR_1`**, **`ARBITRATOR_2`**, **`ARBITRATOR_3`**: Dispute voters.
- **`OBSERVER`**: A guest user who has no wallet and browses read-only.

---

## 3. Simulator Control Guide

### 3.1 Setup Playwright
If Playwright is not yet installed in the dashboard directory:
```bash
cd dashboard
npm install -D @playwright/test
npx playwright install chromium
```

### 3.2 Injecting Session State (JWTs)
Since Playwright cannot interact with Pera/Defly browser extensions directly, you must bypass the extension login by injecting the authenticated JWT and address directly into `localStorage` before navigating:

```typescript
import { test, expect } from '@playwright/test';

test('Simulate Creator Posting Bounty', async ({ page }) => {
  // 1. Set localStorage auth credentials
  await page.addInitScript((credentials) => {
    window.localStorage.setItem('algobounty_jwt', credentials.jwt);
    // If the application stores wallet status or addresses:
    window.localStorage.setItem('algobounty_address', credentials.address);
    window.localStorage.setItem('algobounty_connected', 'true');
  }, { jwt: 'CREATOR_JWT_HERE', address: 'CREATOR_ADDRESS_HERE' });

  // 2. Navigate to site
  await page.goto('http://localhost:3000/create');
  
  // 3. Form input and submission...
});
```

### 3.3 Critical Constraints (No Synthetic Mockups)
> [!IMPORTANT]
> **NEVER generate synthetic screenshots using image generation tools (e.g. `generate_image`, Stable Diffusion, Flux, or DALL-E) to mock user experience flows.**
> All screenshots embedded in UX audit reports MUST be captured directly from a live running application instance using Playwright's native `page.screenshot()` capability.
> If the local environment (e.g. sandbox, database, or uvicorn servers) is not running or lacks the necessary state, you must spin up the local services (or mock the API responses at the HTTP/network layer in Playwright) to run the actual browser test.

---

## 4. Execution Workflow

To run a proxy user test:

### Step 1: Generate the Persona & Scenario
Use the `algo-bounty-user-experience` skill to:
1. Define the persona (e.g. `novice` project creator named Alice, low patience, using desktop).
2. Define the path (e.g. Alice creates a bounty of 150 ALGO, requiring 10 karma).

### Step 2: Initialize Wallets & Auth
Run the wallet factory to authenticate the required actors and get their JWTs:
```bash
python .agents/skills/proxy-user-experience/scripts/wallet-factory.py --auth http://localhost:8000 --json > session_tokens.json
```

### Step 3: Run Playwright Script
Execute the test runner. The test script must:
1. Use viewports matching the persona config.
2. Introduce simulated human delays (e.g., typing delay 100-300ms, reading pauses) scaled by the persona's `attention_span` and `patience`.
3. Capture full-page screenshots at milestone transitions (e.g., wallet connected, form filled, modal open, final receipt).
4. Capture element-level screenshots of key components (like the `FeeBreakdownTable` or `Modal`).
5. Measure page transition times, button response latency, and task completion time.

### Step 4: Gather Innermost Thoughts
During execution, annotate each step with the persona's **inner monologue** generated by `algo-bounty-user-experience`:
- Alice sees the connection screen: *"Why is it asking for a transaction signature just to log in? Is this safe? I'm nervous."*
- Alice fills out the bounty: *"150 ALGO... okay, I filled the form, let's click post."*
- Alice views the fee modal: *"Wait, what is 'Developer Royalty'? Why is 1.5 ALGO going to my own address as royalty if I'm the creator? Oh, it says skipped. That's a bit weird."*

---

## 5. Report Generation

Once execution completes, generate the two required report files under the artifacts directory (`<appDataDir>\brain\<conversation_id>\`):

### 5.1 Visually Appealing HTML Report
- **File Path**: `<appDataDir>\brain\<conversation_id>\ux_report_<persona_id>.html`
- **Source Template**: `.agents/skills/proxy-user-experience/resources/report-template.html`
- **Format**: Injects captured screenshots, timing data, heuristic radar charts, and inner monologues into the interactive template.

### 5.2 Engineering Specs List
- **File Path**: `<appDataDir>\brain\<conversation_id>\ux_engineering_specs_<persona_id>.md`
- **Format**: Markdown with severity-ranked UX findings.
- **Goal**: Ready to be consumed by `/speckit-specify` for system remediation.

---

## 6. Living Design System Updates

If the Playwright run or the UX analysis uncovers visual discrepancies, accessibility gaps, or undocumented UI classes:
1. Load `algo-bounty-style` skill.
2. Edit its `SKILL.md` file to update tokens, add component classes, or update WCAG status.
3. Append a clear record to the `algo-bounty-style` Change Log.

---

## 7. E2E Sandbox and Local Testing Heuristics

When running E2E simulation tests locally with Playwright and a fallback sandbox environment, always adhere to the following troubleshooting rules:

### 7.1 Frontend API Configuration
* **Port Mapping**: When running the Next.js frontend developer server standalone (`npm run dev`), make sure `NEXT_PUBLIC_API_URL` is defined in `dashboard/.env.local` (e.g. `NEXT_PUBLIC_API_URL=http://localhost:8000`). If missing, Next.js will intercept client API calls (such as `/api/v1/agents/me`) and return 404 (Not Found).

### 7.2 Session & Signature Mocking
* **Instant Session Hydration**: In `AuthProvider.tsx`, evaluate the E2E bypass flag (`window.localStorage.getItem('algobounty_connected') === 'true'`) at the very top of the connection `useEffect` hook, before checking if the wallet manager `isReady`. This prevents blocking in headless test contexts where real wallet extensions are unavailable.
* **Blank Transaction Signatures**: When E2E mocking is active, have the frontend `signTransaction` return `""` (empty string). In sandbox mode, the backend accepts empty signature strings and skips transaction broadcasting, allowing updates to succeed database-side without node errors.
* **Standard Algorand Bytes Signature Prefix**: Standard Algorand byte verification (used by the backend `verify_bytes` handler) prepends the message with a `"MX"` prefix for domain separation. Deterministic Python signers (like `wallet-factory.py`) must manually prefix the challenge bytes with `b"MX"` before signing to pass verify checks.

### 7.3 Backend Sandbox Resiliency
* **Mock Application IDs**: During bounty creation in sandbox mode, assign a random 8-digit application ID (e.g. via `random.randint`) when `app_id` is not supplied by the transaction, preventing subsequent `/claim/txn` and `/approve/txn` endpoints from failing on null values.
* **Offline suggested_params Fallback**: Wrap `client.suggested_params()` in a try-except block that returns a mock `SuggestedParams` object if the local sandbox algod node is offline or unreachable, keeping backend preparation endpoints fully responsive.

### 7.4 Multimodal Persona Simulation & Monologue Alignment
* **Visual Understanding Requirement**: Instead of using static/hardcoded monologues in generation templates, future simulations must use a multimodal sub-agent (e.g. a visual model) loaded with the persona's JSON metadata (web3 literacy, technical level, attention span, wallet access).
* **Objective Screenshot Evaluation**: The visual sub-agent must inspect each captured Playwright screenshot to generate objective 3rd-person observations, realistic emotional reactions (monologues), and UX timing diagnostics.
* **Alignment Checklist**:
  - Button labels (e.g. reference "Post Bounty" in the top-left rather than a speculative button on the right).
  - Component positions and visibility states.
  - Loading states (never describe scanning a QR code or spinning widgets unless they are visually captured in the screenshot).
  - Archetype perspective alignment (e.g., Step 4 claim confirmation must be narrated from Bob the worker's perspective, not Alice the creator's).

