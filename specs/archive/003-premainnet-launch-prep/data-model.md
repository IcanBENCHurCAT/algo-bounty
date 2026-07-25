# Data Model: Pre-Mainnet Launch Preparation & Final Hardening

## 1. Smart Contract Box Storage Schema (`escrow.py`)

### `platform_fee` (Box<UInt64>)
- **Key**: `"platform_fee"` (`Bytes`)
- **Value**: `UInt64` (Basis points: e.g. 200 = 2.0%, 150 = 1.5%)
- **Default**: 200 (2.0%)
- **Validation**: $1 \le \text{platform\_fee} \le 1000$ (Max 10.0%)
- **Lifecycle**: Created during `create_bounty()`, deleted upon contract completion in `approve_work()`, `claim_abandoned()`, or `resolve_dispute()`.

---

## 2. API & Frontend Schemas

### `AdminResolveRequest` (Gateway Schema)
```python
class AdminResolveRequest(BaseModel):
    resolution: str  # "worker_win" | "creator_win" | "split"
    reason: Optional[str] = "Admin review completed"
```

### `QuarantineResolveRequest` (Gateway Schema)
```python
class QuarantineResolveRequest(BaseModel):
    action: str  # "clear" | "penalize"
    resolution_note: Optional[str] = "Admin review completed"
    karma_penalty: Optional[int] = 0
```

### `TermsConsentRecord` (Frontend & DB)
- **address**: `str` (Algorand wallet address)
- **accepted_at**: `datetime` (ISO timestamp)
- **terms_version**: `str` (e.g. `"v1.0.0-premainnet"`)
