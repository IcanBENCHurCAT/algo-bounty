from typing import Optional
from pydantic import BaseModel

# Pydantic Schemas
class AuthRequest(BaseModel):
    address: str

class AuthVerify(BaseModel):
    address: str
    signature: str
    challenge: str

class BountyCreate(BaseModel):
    description: str
    amount: int
    asset_id: int = 0
    hitm: bool = False
    repo_url: str
    karma_requirement: int = 0
    github_issue: Optional[int] = None
    hitm_review_days: int = 7
    signed_txn: Optional[str] = None
    app_id: Optional[int] = None
    bounty_id: Optional[str] = None

class BountyDeployResponse(BaseModel):
    unsigned_txns: list[str]
    bounty_id: str
    app_id: int

class BountyClaim(BaseModel):
    signed_txn: str

class WorkSubmit(BaseModel):
    pr_url: str
    proof_data: Optional[dict] = None
    signed_txn: Optional[str] = None

class WorkApprove(BaseModel):
    signed_txn: Optional[str] = None

class WorkReject(BaseModel):
    reason: str
    signed_txn: Optional[str] = None

class DisputeCreate(BaseModel):
    reason: str
    signed_txn: Optional[str] = None

# ─── Fee Breakdown Schemas (FR-002, FR-004) ──────────────────────────────

class FeeBreakdown(BaseModel):
    """Exact integer-division fee amounts matching the on-chain contract."""
    escrow_amount: int  # microALGO
    developer_royalty: int  # 1%: escrow * 2 // 100 // 2
    platform_treasury: int  # 1%: escrow * 2 // 100 // 2
    mediator_fee: int  # 0.25%: escrow * 25 // 10000 (only if HITM)
    claimant_payout: int  # escrow - royalty - treasury - mediator
class FeeBreakdownDisplay(BaseModel):
    """Human-readable display strings for the frontend modal."""
    total: str
    developer_royalty: str
    platform_treasury: str
    mediator_fee: str
    claimant_payout: str
