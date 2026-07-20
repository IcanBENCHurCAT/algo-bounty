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
    platform_fee: int = 200
    treasury_address: Optional[str] = None

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


class AgentProfileResponse(BaseModel):
    address: str
    karma: int
    completed_bounties: int
    disputes_lost: int

class AlgorandHealthResponse(BaseModel):
    status: str
    network: str
    algod: Optional[bool] = None
    indexer: Optional[bool] = None
    error: Optional[str] = None

class AssetHolder(BaseModel):
    asset_id: Optional[int] = None
    amount: int

class AlgorandBalanceResponse(BaseModel):
    address: str
    balance: int
    balance_algo: float
    total_assets: Optional[int] = None
    assets: Optional[list[AssetHolder]] = None
    error: Optional[str] = None

class AssetHolderRecord(BaseModel):
    address: str
    amount: int

class AlgorandAssetHoldersResponse(BaseModel):
    asset_id: int
    total_holders: int
    holders: list[AssetHolderRecord]
    error: Optional[str] = None

class ArbitratorRegistrationResponse(BaseModel):
    status: str
    address: str

class ArbitratorVoteResponse(BaseModel):
    status: str
    bounty_id: str
    vote: str
    tx_id: Optional[str] = None

class AuthChallengeResponse(BaseModel):
    challenge: str
    expires_at: str

class AuthVerifyResponse(BaseModel):
    jwt: str
    address: str
    expires_at: str
    karma: int

class BountyResponse(BaseModel):
    bounty_id: str
    app_id: Optional[int] = None
    status: str
    creator: str
    worker: Optional[str] = None
    amount: int
    asset_id: int
    asset_name: str
    hitm: bool
    description: Optional[str] = None
    repo_url: Optional[str] = None
    karma_requirement: int
    created_at: str
    rejection_count: int
    treasury_altered: bool

class ListBountiesResponse(BaseModel):
    bounties: list[BountyResponse]
    total: int

class BountyCreateResponse(BaseModel):
    bounty_id: str
    app_id: Optional[int] = None
    status: str
    tx_id: Optional[str] = None
    onchain: bool

class BountyActionResponse(BaseModel):
    bounty_id: str
    status: str
    worker: Optional[str] = None
    tx_id: Optional[str] = None
    payout_type: Optional[str] = None
    rejection_count: Optional[int] = None

class BountyOnchainResponse(BaseModel):
    bounty_id: str
    onchain: bool
    app_id: Optional[int] = None
    confirmed_round: Optional[int] = None
    state: Optional[str] = None
    error: Optional[str] = None
    status: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    message: str
    read: bool
    created_at: str

class MarkNotificationReadResponse(BaseModel):
    status: str

class OIDCVerifyResponse(BaseModel):
    status: str
    payload: Optional[dict] = None

class WebhookResponse(BaseModel):
    status: str
    delivery_id: Optional[str] = None
    reason: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    version: str
    sandbox_active: bool
    node_env: str

class EventStreamResponse(BaseModel):
    pass # SSE endpoint, returns a text/event-stream
