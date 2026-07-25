# Implementation Plan: Pre-Mainnet Launch Preparation & Final Hardening

**Branch**: `003-premainnet-launch-prep` | **Date**: July 25, 2026 | **Spec**: [specs/003-premainnet-launch-prep/spec.md](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/specs/003-premainnet-launch-prep/spec.md)

**Input**: Feature specification from `/specs/003-premainnet-launch-prep/spec.md`

---

## Summary

This feature implements the three key architectural prerequisites identified by the Council of Three debate prior to Mainnet deployment:
1. **Platform Fee Parameterization**: Dynamically pass and store `platform_fee` basis points in `escrow.py` box storage per bounty deployment so fee rates can be tuned while keeping PyTEAL approval bytecode 100% frozen and immutable.
2. **Dedicated Admin Dashboard Portal**: Create `/admin` page in `dashboard/` providing 1-click visual dispute resolution (`Worker Win`, `Creator Win`, `Split`) and account quarantine clearance for `ADMIN_ADDRESS`.
3. **Mandatory Terms of Service (ToS)**: Integrate `TermsModal.tsx` in `dashboard/` disclaiming custodial software status, establishing FAA arbitration consent, and clarifying Phase 1 best-effort admin stewardship.

---

## Technical Context

**Language/Version**: Python 3.12+ (FastAPI backend, `algopy` PyTEAL smart contract), TypeScript / Next.js 14+ (App Router dashboard).  
**Primary Dependencies**: FastAPI, SQLAlchemy, `py-algorand-sdk`, `@txnlab/use-wallet`, Tailwind CSS, Lucide Icons.  
**Storage**: Algorand Global Box Storage (`platform_fee` box), Supabase PostgreSQL / local SQLite (`bounties`, `account_quarantines`), `localStorage` (ToS consent).  
**Testing**: `pytest`, `pytest-asyncio`, `npx tsc --noEmit`.  
**Target Platform**: Algorand Testnet/Mainnet, Docker Compose / GCP Cloud Run.  
**Project Type**: Decentralized bounty platform (Smart Contracts + FastAPI Gateway + Next.js Frontend).  
**Performance Goals**: API response $< 200\text{ms}$, `/admin` dashboard load $< 500\text{ms}$.  
**Constraints**: Zero RekeyTo vulnerabilities, mandatory HITM default, strict admin authorization dependencies.  

---

## Constitution Check

- [X] **Smart Contract Language**: Written in Algorand Python (`algopy` / PyTEAL framework) compiled via Puya (`compile_teal.py`).
- [X] **RekeyTo Protection**: Protected by `assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))` across 100% of state-modifying ABI methods.
- [X] **Box Storage Limits**: `platform_fee` stored as `Box(UInt64)`.
- [X] **Database Compatibility**: Async/Sync SQLAlchemy models compatible with PostgreSQL and SQLite.
- [X] **Admin Security**: Endpoints protected by `is_admin` dependency checking `ADMIN_ADDRESS`.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-premainnet-launch-prep/
├── plan.md              # This implementation plan
├── spec.md              # Feature specification
├── research.md          # Architectural decisions & research
├── data-model.md        # Data models & box storage schemas
├── quickstart.md        # Validation guide
├── contracts/
│   └── admin-api.md     # Admin API contracts
└── checklists/
    └── requirements.md  # Quality checklist
```

---

## Proposed Changes

### 1. Smart Contract Layer (`escrow.py`)

#### [MODIFY] [escrow.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/escrow.py)
- Add `self.platform_fee = Box(UInt64, key="platform_fee")` in `EscrowContract.__init__()`.
- Accept `platform_fee: UInt64` in `create_bounty()`, validate $1 \le \text{platform\_fee} \le 1000$, and store in box.
- Update `_send_payout_with_royalties()` to compute `fee_platform = (escrow_amount * self._get_platform_fee()) // 10000`.
- Delete `platform_fee` box upon contract finalization.
- Recompile TEAL artifacts via `compile_teal.py`.

### 2. Backend Gateway (`gateway/`)

#### [MODIFY] [gateway/schemas.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/gateway/schemas.py)
- Ensure `BountyCreate` includes optional `platform_fee: Optional[int] = 200` (default 200 bps / 2.0%).

#### [MODIFY] [gateway/routers/bounties.py](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/gateway/routers/bounties.py)
- Pass `platform_fee` to contract creation helper.

### 3. Frontend Dashboard (`dashboard/`)

#### [NEW] [dashboard/src/app/admin/page.tsx](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/dashboard/src/app/admin/page.tsx)
- Create Admin Management Dashboard with tabs for "Disputed Bounties" and "Account Quarantines".
- Restrict access to `ADMIN_ADDRESS` wallet.
- Implement 1-click dispute resolution buttons (`Worker Win`, `Creator Win`, `Split`).
- Implement 1-click quarantine resolution buttons (`Clear`, `Penalize`).

#### [NEW] [dashboard/src/components/TermsModal.tsx](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/dashboard/src/components/TermsModal.tsx)
- Create Terms of Service modal disclaiming custodial status, detailing FAA arbitration consent, and explaining Phase 1 stewardship rules.

#### [MODIFY] [dashboard/src/components/DashboardLayout.tsx](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/dashboard/src/components/DashboardLayout.tsx)
- Add conditional "Admin" link in navigation bar visible when `connectedAddress === ADMIN_ADDRESS`.

#### [MODIFY] [dashboard/src/lib/api.ts](file:///c:/Users/Garret/.gemini/antigravity/scratch/algo-bounty/dashboard/src/lib/api.ts)
- Add `getQuarantines()`, `resolveQuarantine()`, and `adminResolveDispute()` client methods.

---

## Verification Plan

### Automated Tests
```bash
# Test smart contract fee split logic with dynamic fee rates
PYTHONPATH=. python -m pytest tests/test_fee_split.py -v

# Test admin dispute resolution and quarantine endpoints
PYTHONPATH=. python -m pytest tests/test_admin_disputes.py tests/test_quarantine.py -v

# Check TypeScript compilation
cd dashboard && npx tsc --noEmit
```
