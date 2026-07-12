import re

with open('dashboard/src/app/profile/page.tsx', 'r') as f:
    content = f.read()

# Imports
content = content.replace("import { getMyProfile } from '@/lib/api'", "import { getMyProfile, getBounties } from '@/lib/api'")
content = content.replace("import type { AgentProfile } from '@/types'", "import type { AgentProfile, Bounty } from '@/types'")
content = content.replace("import { Button } from '@/components/ui/Button'", "import { Button }\nimport { StatusBadge } from '@/components/ui/Badge'")

# Add BountyRow and formatAlgo functions
bounty_row = """
function formatAlgo(micro: number) {
  const a = micro / 1_000_000
  return `${a % 1 === 0 ? a.toFixed(0) : a.toFixed(4)} ALGO`
}

function BountyRow({ bounty }: { bounty: Bounty }) {
  return (
    <Link href={`/bounties/${bounty.bounty_id}`} style={{ textDecoration: 'none' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          padding: '0.875rem 1rem',
          borderRadius: '0.625rem',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.05)',
          transition: 'background 0.15s, border-color 0.15s',
          cursor: 'pointer',
          flexWrap: 'wrap',
        }}
        onMouseEnter={(e) => {
          ;(e.currentTarget as HTMLElement).style.background = 'rgba(99,102,241,0.06)'
          ;(e.currentTarget as HTMLElement).style.borderColor = 'rgba(99,102,241,0.2)'
        }}
        onMouseLeave={(e) => {
          ;(e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)'
          ;(e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.05)'
        }}
      >
        <StatusBadge status={bounty.status} />
        <span style={{ flex: 1, color: '#cbd5e1', fontSize: '0.9375rem', minWidth: '200px' }}>
          {bounty.description && bounty.description.length > 80
            ? bounty.description.slice(0, 80) + '…'
            : bounty.description}
        </span>
        <span style={{ color: '#22d3ee', fontWeight: 700, fontSize: '0.9375rem', whiteSpace: 'nowrap' }}>
          {formatAlgo(bounty.amount)}
        </span>
      </div>
    </Link>
  )
}
"""
content = content.replace("// ─── Page ─────────────────────────────────────────────────────────────────────", bounty_row + "\n\n// ─── Page ─────────────────────────────────────────────────────────────────────")

# Update ProfilePage component
search_block = """export default function ProfilePage() {
  const { connected, address, jwt, karma, profile: authProfile, disconnect, refreshProfile } =
    useAuth()
  const toast = useToast()

  const [profile, setProfile] = useState<AgentProfile | null>(authProfile)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setProfile(authProfile)
  }, [authProfile])

  useEffect(() => {
    if (!connected || !jwt) return
    setLoading(true)
    getMyProfile(jwt)
      .then(setProfile)
      .catch(() => null)
      .finally(() => setLoading(false))
  }, [connected, jwt])"""

replace_block = """type Tab = 'created' | 'claimed' | 'completed' | 'disputed'

export default function ProfilePage() {
  const { connected, address, jwt, karma, profile: authProfile, disconnect, refreshProfile } =
    useAuth()
  const toast = useToast()

  const [profile, setProfile] = useState<AgentProfile | null>(authProfile)
  const [loading, setLoading] = useState(false)
  const [bountiesLoading, setBountiesLoading] = useState(false)

  const [tab, setTab] = useState<Tab>('created')
  const [bounties, setBounties] = useState<Bounty[]>([])

  useEffect(() => {
    setProfile(authProfile)
  }, [authProfile])

  useEffect(() => {
    if (!connected || !jwt) return
    setLoading(true)
    getMyProfile(jwt)
      .then(setProfile)
      .catch(() => null)
      .finally(() => setLoading(false))
  }, [connected, jwt])

  useEffect(() => {
    if (!connected || !address) return
    setBountiesLoading(true)

    // Determine filters based on tab
    const filters: any = { limit: 50 }
    if (tab === 'created') {
      filters.creator = address
    } else {
      filters.worker = address
      if (tab === 'claimed') filters.status = 'claimed'
      if (tab === 'completed') filters.status = 'closed'
      if (tab === 'disputed') filters.status = 'disputed'
    }

    getBounties(filters)
      .then(res => setBounties(res.bounties))
      .catch(() => setBounties([]))
      .finally(() => setBountiesLoading(false))
  }, [connected, address, tab])"""

content = content.replace(search_block, replace_block)

# Update return statement
search_block = """      {/* Account details */}
      <div style={sectionStyle}>
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
          Account
        </h2>"""

replace_block = """      {/* Bounty tabs */}
      <div style={sectionStyle}>
        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.75rem', overflowX: 'auto' }}>
          {(['created', 'claimed', 'completed', 'disputed'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: '0.375rem 1rem',
                borderRadius: '0.5rem',
                border: 'none',
                background: tab === t ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: tab === t ? '#818cf8' : '#475569',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: tab === t ? 700 : 400,
                transition: 'all 0.15s',
                textTransform: 'capitalize',
                whiteSpace: 'nowrap'
              }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Bounty list */}
        {bountiesLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {[...Array(3)].map((_, i) => <SkeletonCard key={i} height="3.5rem" />)}
          </div>
        ) : bounties.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#475569' }}>
            No bounties to display
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {bounties.map((b) => (
              <BountyRow key={b.bounty_id} bounty={b} />
            ))}
          </div>
        )}
      </div>

      {/* Account details */}
      <div style={sectionStyle}>
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
          Account
        </h2>"""
content = content.replace(search_block, replace_block)

# Remove "View Marketplace" link
search_block = """      {/* Quick links */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <Link href="/">
          <Button variant="ghost">View Marketplace</Button>
        </Link>
        <Link href="/create">
          <Button>+ Create Bounty</Button>
        </Link>"""
replace_block = """      {/* Quick links */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <Link href="/create">
          <Button>+ Create Bounty</Button>
        </Link>"""
content = content.replace(search_block, replace_block)

with open('dashboard/src/app/profile/page.tsx', 'w') as f:
    f.write(content)
