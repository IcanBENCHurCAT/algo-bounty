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
