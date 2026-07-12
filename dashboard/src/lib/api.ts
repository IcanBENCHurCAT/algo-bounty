import type {
  Bounty,
  BountyListResponse,
  BountyFilters,
  AgentProfile,
  AuthChallenge,
  AuthResponse,
  NotificationItem,
  EscrowState,
  EscrowTransaction,
  CreateBountyPayload,
  CreateBountyResponse,
  ApiError,
} from '@/types'
import { AlgoBountyError } from '@/types'

// ─── Config ───────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''
const JWT_KEY = 'algobounty_jwt'

// ─── Token helpers ────────────────────────────────────────────────────────────

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(JWT_KEY)
}

export function storeToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(JWT_KEY, token)
}

export function clearToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(JWT_KEY)
}

// ─── Fetch wrapper ────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    let errorBody: { error?: ApiError } = {}
    try {
      errorBody = await res.json()
    } catch {
      // ignore parse errors
    }
    const err = errorBody.error
    throw new AlgoBountyError(
      err?.code ?? 'UnknownError',
      err?.message ?? `HTTP ${res.status}`,
      err?.details,
    )
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

// ─── Bounty endpoints ─────────────────────────────────────────────────────────

export async function getBounties(
  filters: BountyFilters = {},
): Promise<BountyListResponse> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.hitm && filters.hitm !== 'any') params.set('hitm', filters.hitm)
  if (filters.minAmount != null)
    params.set('min_amount', String(Math.round(filters.minAmount * 1_000_000)))
  if (filters.maxAmount != null)
    params.set('max_amount', String(Math.round(filters.maxAmount * 1_000_000)))
  if (filters.repo) params.set('repo', filters.repo)
  if (filters.minKarma != null) params.set('min_karma', String(filters.minKarma))
  if (filters.sortBy) params.set('sort', filters.sortBy)
  if (filters.page) params.set('page', String(filters.page))
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.creator) params.set('creator', filters.creator)
  if (filters.worker) params.set('worker', filters.worker)

  const qs = params.toString()
  return apiFetch<BountyListResponse>(`/api/v1/bounties${qs ? `?${qs}` : ''}`)
}

export async function getBounty(bountyId: string): Promise<Bounty> {
  return apiFetch<Bounty>(`/api/v1/bounties/${bountyId}`)
}

export async function createBounty(
  payload: CreateBountyPayload,
  token: string,
): Promise<CreateBountyResponse> {
  return apiFetch<CreateBountyResponse>('/api/v1/bounties', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, token)
}

export async function getClaimTxn(
  bountyId: string,
  token: string,
): Promise<{ unsigned_txn: string }> {
  return apiFetch<{ unsigned_txn: string }>(
    `/api/v1/bounties/${bountyId}/claim/txn`,
    { method: 'POST' },
    token,
  )
}

export async function claimBounty(
  bountyId: string,
  signedTxn: string,
  token: string,
): Promise<{ bounty_id: string; status: string; worker_address: string }> {
  return apiFetch(
    `/api/v1/bounties/${bountyId}/claim`,
    { method: 'POST', body: JSON.stringify({ signed_txn: signedTxn }) },
    token,
  )
}

export async function submitWork(
  bountyId: string,
  payload: { pr_url: string; proof_data?: Record<string, unknown> },
  token: string,
): Promise<{ bounty_id: string; status: string; review_deadline: string }> {
  return apiFetch(
    `/api/v1/bounties/${bountyId}/submit`,
    { method: 'POST', body: JSON.stringify(payload) },
    token,
  )
}

export async function getApproveTxn(
  bountyId: string,
  token: string,
): Promise<{ unsigned_txn: string }> {
  return apiFetch<{ unsigned_txn: string }>(
    `/api/v1/bounties/${bountyId}/approve/txn`,
    { method: 'POST' },
    token,
  )
}

export async function approveWork(
  bountyId: string,
  signedTxn: string,
  token: string,
): Promise<{ bounty_id: string; status: string; payout_amount: number }> {
  return apiFetch(
    `/api/v1/bounties/${bountyId}/approve`,
    { method: 'POST', body: JSON.stringify({ signed_txn: signedTxn }) },
    token,
  )
}

export async function rejectWork(
  bountyId: string,
  token: string,
  reason?: string,
): Promise<{ bounty_id: string; status: string }> {
  return apiFetch(
    `/api/v1/bounties/${bountyId}/reject`,
    { method: 'POST', body: JSON.stringify({ reason }) },
    token,
  )
}

export async function disputeWork(
  bountyId: string,
  token: string,
  reason?: string,
): Promise<{ bounty_id: string; status: string }> {
  return apiFetch(
    `/api/v1/bounties/${bountyId}/dispute`,
    { method: 'POST', body: JSON.stringify({ reason }) },
    token,
  )
}

export async function abandonBounty(
  bountyId: string,
  token: string,
): Promise<{ bounty_id: string; status: string }> {
  return apiFetch(
    `/api/v1/bounties/${bountyId}`,
    { method: 'DELETE' },
    token,
  )
}

// ─── Agent endpoints ──────────────────────────────────────────────────────────

export async function getAgentProfile(address: string): Promise<AgentProfile> {
  return apiFetch<AgentProfile>(`/api/v1/agents/${address}`)
}

export async function getMyProfile(token: string): Promise<AgentProfile> {
  return apiFetch<AgentProfile>('/api/v1/agents/me', {}, token)
}

// ─── Auth endpoints ───────────────────────────────────────────────────────────

export async function requestChallenge(address: string): Promise<AuthChallenge> {
  return apiFetch<AuthChallenge>('/api/v1/auth/request', {
    method: 'POST',
    body: JSON.stringify({ address }),
  })
}

export async function verifyAuth(
  address: string,
  signature: string,
  challenge: string,
): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/v1/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ address, signature, challenge }),
  })
}

// ─── Notification endpoints ───────────────────────────────────────────────────

export async function getNotifications(
  token: string,
): Promise<NotificationItem[]> {
  return apiFetch<NotificationItem[]>('/api/v1/notifications', {}, token)
}

export async function markNotificationRead(
  id: number,
  token: string,
): Promise<void> {
  return apiFetch<void>(
    `/api/v1/notifications/${id}/read`,
    { method: 'POST' },
    token,
  )
}

export async function markAllNotificationsRead(token: string): Promise<void> {
  // Mark each unread notification as read
  const notifications = await getNotifications(token)
  const unread = notifications.filter((n) => !n.read)
  await Promise.all(unread.map((n) => markNotificationRead(n.notification_id, token)))
}

// ─── Escrow endpoints ─────────────────────────────────────────────────────────

export async function getEscrow(appId: number): Promise<EscrowState> {
  return apiFetch<EscrowState>(`/api/v1/escrows/${appId}`)
}

export async function getEscrowTransactions(
  appId: number,
): Promise<EscrowTransaction[]> {
  return apiFetch<EscrowTransaction[]>(`/api/v1/escrows/${appId}/transactions`)
}
