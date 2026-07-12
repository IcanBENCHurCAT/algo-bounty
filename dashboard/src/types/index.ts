// ─── Bounty ───────────────────────────────────────────────────────────────────

export type BountyStatus =
  | 'open'
  | 'claimed'
  | 'submitted'
  | 'approved'
  | 'disputed'
  | 'refunded'
  | 'closed'

export interface Bounty {
  bounty_id: string
  app_id: number | null
  status: BountyStatus
  creator: string
  worker: string | null
  amount: number // microALGO
  asset_id: number
  asset_name: string
  hitm: boolean
  deadline_round: number | null
  deadline_rounds_remaining: number | null
  deadline_timestamp: string | null
  description: string
  repo_url: string | null
  repo_labels: string[]
  karma_required: number
  created_at: string
  updated_at: string
  tags: string[]
  github_issue: number | null
}

export interface BountyListResponse {
  bounties: Bounty[]
  total: number
  page: number
  limit: number
  has_more: boolean
}

export interface BountyFilters {
  status?: string
  hitm?: 'any' | 'true' | 'false'
  minAmount?: number // in ALGO (converted to microALGO for API)
  maxAmount?: number // in ALGO
  repo?: string
  minKarma?: number
  sortBy?: 'created_at' | 'amount' | 'karma_required' | 'deadline'
  page?: number
  limit?: number
}

// ─── Agent / Profile ──────────────────────────────────────────────────────────

export interface AgentProfile {
  address: string
  karma: number
  reputation_score: number
  bounties_created: number
  bounties_claimed: number
  bounties_completed: number
  bounties_disputed: number
  bounties_rejected: number
  novice_tier: boolean
  novice_count: number
  avg_review_time: string | null
  created_at: string
  updated_at: string
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthChallenge {
  challenge: string
  expires_at: string
}

export interface AuthResponse {
  jwt: string
  address: string
  expires_at: string
  karma: number
}

export interface WalletAuthState {
  address: string | null
  connected: boolean
  walletType: string | null
  jwt: string | null
  karma: number
  profile: AgentProfile | null
  loading: boolean
  error: string | null
}

// ─── Notifications ────────────────────────────────────────────────────────────

export interface NotificationItem {
  id: number
  message: string
  read: boolean
  created_at: string
}

// ─── Escrow ───────────────────────────────────────────────────────────────────

export interface EscrowState {
  app_id: number
  bounty_id: string
  balance: number
  state: string
  payout_type: 'PAYOUT' | 'REFUND' | 'SPLIT' | null
  created_at: string
}

export interface EscrowTransaction {
  txid: string
  round: number
  type: string
  amount: number
  sender: string
  receiver: string
  note: string
  created_at: string
}

// ─── API Error ────────────────────────────────────────────────────────────────

export interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
}

export class AlgoBountyError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message)
    this.name = 'AlgoBountyError'
  }
}

// ─── SSE Events ───────────────────────────────────────────────────────────────

export type SseEventType =
  | 'bounty.created'
  | 'bounty.claimed'
  | 'bounty.submitted'
  | 'bounty.approved'
  | 'bounty.rejected'
  | 'bounty.disputed'
  | 'karma.updated'

export interface SseEvent {
  type: SseEventType
  data: {
    bounty_id?: string
    address?: string
    karma?: number
    [key: string]: unknown
  }
}

// ─── Create Bounty ────────────────────────────────────────────────────────────

export interface CreateBountyPayload {
  description: string
  amount: number // microALGO
  asset_id: number
  hitm: boolean
  deadline_rounds: number
  repo_url: string
  repo_labels: string[]
  karma_requirement: number
  tags: string[]
  github_issue?: number
  hitm_review_days?: number
  signed_txn?: string
  app_id?: number
  bounty_id?: string
}

export interface CreateBountyResponse {
  bounty_id: string
  app_id: number
  signed_txid: string
}
