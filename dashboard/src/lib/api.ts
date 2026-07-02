const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export interface Bounty {
  bounty_id: string;
  app_id: number | null;
  status: string;
  creator: string;
  amount: number;
  asset_id: number;
  asset_name: string;
  hitm: boolean;
  deadline_round: number | null;
  deadline_rounds_remaining: number | null;
  description: string;
  repo_url: string | null;
  repo_labels: string[];
  karma_requirement: number;
  created_at: string;
  tags: string[];
  worker?: string | null;
  github_issue?: number | null;
}

export interface BountyListResponse {
  bounties: Bounty[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface AgentProfile {
  address: string;
  karma: number;
  reputation_score: number;
  bounties_created: number;
  bounties_claimed: number;
  bounties_completed: number;
  bounties_disputed: number;
  bounties_rejected: number;
  novice_tier: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationItem {
  notification_id: number;
  event_type: string;
  read: boolean;
  data: Record<string, unknown> | null;
  created_at: string;
}

export interface AuthChallenge {
  challenge: string;
  expires_at: string;
}

export interface AuthResponse {
  jwt: string;
  address: string;
  expires_at: string;
  karma: number;
}

// --- Token helpers ---

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('algobounty_jwt');
}

export function storeToken(jwt: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('algobounty_jwt', jwt);
}

export function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('algobounty_jwt');
}

// --- Bounty endpoints ---

export async function getBounties(
  params: {
    status?: string;
    repo?: string;
    min_amount?: number;
    max_amount?: number;
    min_karma?: number;
    hitm?: string;
    sort?: string;
    page?: number;
    limit?: number;
  } = {},
): Promise<BountyListResponse> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  }
  const res = await fetch(`${API_BASE}/api/v1/bounties?${qs}`);
  if (!res.ok) throw new Error(`Failed to list bounties: ${res.status}`);
  return res.json();
}

export async function getBounty(bountyId: string): Promise<Bounty> {
  const res = await fetch(`${API_BASE}/api/v1/bounties/${bountyId}`);
  if (!res.ok) throw new Error(`Failed to fetch bounty: ${res.status}`);
  return res.json();
}

export async function createBounty(
  body: {
    description: string;
    amount: number;
    hitm?: boolean;
    deadline_rounds?: number;
    repo_url?: string;
    repo_labels?: string[];
    karma_requirement?: number;
    tags?: string[];
    asset_id?: number;
  },
  token: string,
): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/v1/bounties`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || `Failed to create bounty: ${res.status}`);
  }
  return res.json();
}

export async function claimBounty(
  bountyId: string,
  body: { signed_txn: string },
  token: string,
): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/v1/bounties/${bountyId}/claim`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || `Failed to claim bounty: ${res.status}`);
  }
  return res.json();
}

export async function submitWork(
  bountyId: string,
  body: { pr_url: string; proof_data?: Record<string, unknown> },
  token: string,
): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/v1/bounties/${bountyId}/submit`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || `Failed to submit work: ${res.status}`);
  }
  return res.json();
}

export async function approveWork(
  bountyId: string,
  body: { signed_txn?: string },
  token: string,
): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/v1/bounties/${bountyId}/approve`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || `Failed to approve: ${res.status}`);
  }
  return res.json();
}

export async function rejectWork(
  bountyId: string,
  token: string,
  body?: { signed_txn?: string },
): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/v1/bounties/${bountyId}/reject`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || `Failed to reject: ${res.status}`);
  }
  return res.json();
}

export async function disputeWork(
  bountyId: string,
  token: string,
  body?: Record<string, unknown>,
): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/v1/bounties/${bountyId}/dispute`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || `Failed to dispute: ${res.status}`);
  }
  return res.json();
}

// --- Agent / Profile endpoints ---

export async function getAgentProfile(address: string): Promise<AgentProfile> {
  const res = await fetch(`${API_BASE}/api/v1/agents/${address}`);
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`);
  return res.json();
}

export async function getMyProfile(token: string): Promise<AgentProfile> {
  const res = await fetch(`${API_BASE}/api/v1/agents/me`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`);
  return res.json();
}

// --- Auth endpoints ---

export async function requestChallenge(): Promise<AuthChallenge> {
  const res = await fetch(`${API_BASE}/api/v1/auth/request`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to get auth challenge');
  return res.json();
}

export async function verifyAuth(
  address: string,
  signature: string,
  challenge: string,
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/verify`, {
    method: 'POST',
    headers: authHeaders(null),
    body: JSON.stringify({ address, signature, challenge }),
  });
  if (!res.ok) throw new Error('Failed to verify auth');
  return res.json();
}

// --- Notification endpoints ---

export async function getNotifications(token: string): Promise<NotificationItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/notifications`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to fetch notifications: ${res.status}`);
  const body = await res.json();
  return Array.isArray(body) ? body : (body.notifications ?? []);
}

export async function markNotificationRead(
  notificationId: number,
  token: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/notifications/${notificationId}/read`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to mark read: ${res.status}`);
}

// --- Escrow endpoints ---

export async function getEscrow(appId: number): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/v1/escrows/${appId}`);
  if (!res.ok) throw new Error(`Failed to fetch escrow: ${res.status}`);
  return res.json();
}
