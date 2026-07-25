# Research & Architectural Decisions: Pre-Mainnet Launch Preparation & Final Hardening

## 1. Dynamic Platform Fee Parameterization in Smart Contract (`escrow.py`)

### Decision
Parameterize `platform_fee` basis points in `escrow.py` by introducing `self.platform_fee = Box(UInt64, key="platform_fee")` in the PyTEAL `EscrowContract`. Upon bounty initialization in `create_bounty()`, `platform_fee` is passed as an ABI parameter (e.g. 200 for 2.0%) and stored in the contract's box storage.

### Rationale
- Hardcoded literals in PyTEAL require contract bytecode compilation changes whenever fees are tuned.
- Box storage parameterization allows each escrow instance to be initialized with a specific fee rate while keeping approval TEAL bytecode identical and immutable across deployments.
- Default bound enforcement ($\le 1000$ basis points / 10%) prevents accidental or malicious misconfiguration.

### Alternatives Considered
- *TemplateVar[UInt64]*: Requires re-compiling bytecode per fee tier, resulting in distinct App IDs and breaking contract immutability auditing.
- *Global State*: Global state limits in AVM contracts are less flexible than key-value Box storage in Puya PyTEAL.

---

## 2. Dedicated Admin Management Dashboard (`/admin` in `dashboard/`)

### Decision
Build `/admin/page.tsx` in Next.js App Router. Access is restricted client-side via wallet check (`address === ADMIN_ADDRESS`) and server-side via FastAPI `is_admin` security dependency (`X-Admin-Key` or `ADMIN_ADDRESS` JWT claim).

### Rationale
- Reuses existing FastAPI admin routes (`POST /api/v1/admin/disputes/{id}/resolve`, `GET /api/v1/admin/quarantines`, `POST /api/v1/admin/quarantines/{id}/resolve`).
- Eliminates administrative error from raw CLI `curl` calls.
- Offers 1-click dispute resolution (`Worker Win`, `Creator Win`, `Split`) and 1-click quarantine resolution (`Clear`, `Penalize`).

### Alternatives Considered
- *Third-party admin portal (Retool/ForestAdmin)*: Introduces third-party dependency and secret leakage risk for Algorand wallet signatures.

---

## 3. Mandatory Terms of Service (ToS) & Legal Disclaimers

### Decision
Implement `TermsModal.tsx` component in `dashboard/src/components/`. On wallet connection, check `localStorage.getItem("algobounty_tos_accepted")`. If null or outdated version, display the modal. Acceptance is saved locally and synced to backend user preference.

### Rationale
- Complies with FinCEN software provider non-custodial guidelines.
- Establishes explicit FAA arbitration consent and disclaims bailment/custodial liability during Phase 1 pre-mainnet testing.

---

## Summary of Research Decisions

| Feature Component | Chosen Mechanism | Primary Benefit |
| :--- | :--- | :--- |
| **Fee Parameterization** | Box Storage (`self.platform_fee = Box(UInt64)`) | 100% TEAL bytecode immutability |
| **Admin Management** | Next.js `/admin` Dashboard Route | Clean visual UX; zero CLI dependency |
| **Legal ToS** | `TermsModal.tsx` with versioned consent | Regulatory & custodial liability protection |
