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
    gateway_address: Optional[str] = None
    authorized_app_id: Optional[int] = None
    hitm_enforced: Optional[bool] = None


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
    estimated_mediator_fee: Optional[int] = 0  # 0.25% cost if dispute is invoked
    claimant_payout: int  # escrow - royalty - treasury - mediator

class FeeBreakdownDisplay(BaseModel):
    """Human-readable display strings for the frontend modal."""
    total: str
    developer_royalty: str
    platform_treasury: str
    mediator_fee: str
    estimated_mediator_fee: Optional[str] = None
    claimant_payout: str


class AgentProfileResponse(BaseModel):
    address: str
    github_username: Optional[str] = None
    karma: int
    completed_bounties: int
    disputes_lost: int
    # ─── Stewardship fields (Legal #165) ───────────────────────────
    steward_name: Optional[str] = None
    steward_email: Optional[str] = None
    steward_verified: bool = False
    steward_stablecoin_address: Optional[str] = None
    steward_of: Optional[str] = None
    steward_of_steward_address: Optional[str] = None
    # ─── Tax compliance fields (Legal #170) ───────────────────────────
    tax_jurisdiction: Optional[str] = None  # ISO 3166-1 alpha-2 country code
    tax_form_submitted: bool = False  # W-9 (US) or W-8BEN (non-US)
    tax_form_date: Optional[str] = None  # ISO 8601 date of form submission
    cumulative_payouts_year: float = 0.0  # YTD payouts in USD for 1099-K threshold
    tax_withhold_rate: float = 0.0  # Withholding rate (0.0 = none)


class AgentLinkGitHub(BaseModel):
    github_username: str

# ─── Stewardship schemas (Legal #165) ─────────────────────────────────

class StewardRegisterRequest(BaseModel):
    """Register a human steward for the authenticated agent."""
    steward_name: str
    steward_email: str
    steward_stablecoin_address: Optional[str] = None

class StewardRegisterResponse(BaseModel):
    status: str
    steward_name: str
    steward_email: str
    steward_verified: bool


# ─── Tax compliance schemas (Legal #170) ──────────────────────────────────

class TaxUpdateRequest(BaseModel):
    """Update tax info for the authenticated agent."""
    tax_jurisdiction: str  # ISO 3166-1 alpha-2 (e.g. "US", "DE", "GB")
    tax_form: str  # "w-9" or "w-8ben"
    tax_form_date: Optional[str] = None  # ISO 8601; defaults to now
    treaty_benefit: bool = False  # W-8BEN treaty claim


class TaxUpdateResponse(BaseModel):
    status: str
    tax_jurisdiction: str
    tax_form: str
    tax_form_date: str
    treaty_benefit: bool
    cumulative_payouts_year: float
    tax_withhold_rate: float
    needs_withholding: bool


class PayoutSummaryResponse(BaseModel):
    """Cumulative payout summary for 1099-K threshold tracking."""
    agent_address: str
    cumulative_payouts_year: float
    _1099k_threshold: float = 600.0
    exceeded: bool
    tax_jurisdiction: Optional[str]
    tax_form_submitted: bool
    tax_withhold_rate: float


class WithholdingConfigResponse(BaseModel):
    """Tax withholding configuration for an agent."""
    tax_jurisdiction: str
    tax_form: str
    tax_withhold_rate: float
    treaty_benefit: bool
    withholding_description: str


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

class EvaluatorRegistrationResponse(BaseModel):
    status: str
    address: str

class EvaluatorResponse(BaseModel):
    address: str
    status: str
    karma: Optional[int] = 0
    disputes_lost: Optional[int] = 0

class EvaluatorListResponse(BaseModel):
    evaluators: list[EvaluatorResponse]
    total: int
    
class EvaluatorMeResponse(BaseModel):
    address: str
    status: str
    karma: int
    can_register: bool

class EvaluatorVoteResponse(BaseModel):
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
    gateway_address: Optional[str] = None
    authorized_app_id: Optional[int] = None
    hitm_enforced: Optional[bool] = False


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

class SyncGithubResponse(BaseModel):
    status: str
    bounty_id: str
    github_state: str
    previous_status: Optional[str] = None
    current_status: Optional[str] = None
    payout_ready: bool
    message: str

class ClaimPayoutResponse(BaseModel):
    status: str
    bounty_id: str
    tx_id: Optional[str] = None
    amount: Optional[int] = None
    message: str

class AdminResolveRequest(BaseModel):
    resolution: str  # "worker_win", "creator_win", or "split"
    reason: Optional[str] = "Admin dispute resolution"

class AdminResolveResponse(BaseModel):
    status: str
    bounty_id: str
    resolution: str
    tx_id: Optional[str] = None
    message: str
