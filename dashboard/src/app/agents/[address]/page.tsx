'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { getAgentProfile, getBounties } from '@/lib/api'
import type { AgentProfile, Bounty } from '@/types'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { FullPageSpinner } from '@/components/ui/Spinner'
import { SkeletonCard } from '@/components/ui/Skeleton'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatAlgo(micro: number) {
  const a = micro / 1_000_000
  return `${a % 1 === 0 ? a.toFixed(0) : a.toFixed(4)} ALGO`
}

function truncateAddress(addr: string) {
  return `${addr?.slice(0, 14)}…${addr?.slice(-6)}`
}

// ─── Address display ──────────────────────────────────────────────────────────

function AddressDisplay({ address }: { address: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    void navigator.clipboard.writeText(address)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
      <span
        style={{
          fontFamily: 'monospace',
          fontSize: '0.9375rem',
          color: '#a5b4fc',
          background: 'rgba(99,102,241,0.08)',
          padding: '0.375rem 0.75rem',
          borderRadius: '0.5rem',
          letterSpacing: '0.02em',
        }}
      >
        {address?.slice(0, 20)}…{address?.slice(-8)}
      </span>
      <button
        onClick={handleCopy}
        style={{
          background: 'none',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '0.375rem',
          color: copied ? '#10b981' : '#475569',
          cursor: 'pointer',
          fontSize: '0.75rem',
          padding: '0.25rem 0.625rem',
          transition: 'all 0.15s',
        }}
      >
        {copied ? '✓ Copied' : 'Copy'}
      </button>
    </div>
  )
}

// ─── Bounty Row ───────────────────────────────────────────────────────────────

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

// ─── Page ─────────────────────────────────────────────────────────────────────

type Tab = 'created' | 'claimed' | 'completed' | 'disputed'

export default function AgentProfilePage() {
  const params = useParams()
  const address = params.address as string

  const [profile, setProfile] = useState<AgentProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(true)
  const [bountiesLoading, setBountiesLoading] = useState(false)

  const [tab, setTab] = useState<Tab>('created')

  const [createdBounties, setCreatedBounties] = useState<Bounty[]>([])
  const [claimedBounties, setClaimedBounties] = useState<Bounty[]>([])
  const [completedBounties, setCompletedBounties] = useState<Bounty[]>([])
  const [disputedBounties, setDisputedBounties] = useState<Bounty[]>([])

  // Fetch profile
  useEffect(() => {
    setProfileLoading(true)
    getAgentProfile(address)
      .then(setProfile)
      .catch(() => null)
      .finally(() => setProfileLoading(false))
  }, [address])

  const fetchBounties = useCallback(async () => {
    if (!address) return
    setBountiesLoading(true)
    try {
      const [created, worked] = await Promise.allSettled([
        getBounties({ limit: 50, creator: address }),
        // API does not support worker filter yet, fetch latest and filter locally
        getBounties({ limit: 50 }),
      ])

      if (created.status === 'fulfilled') {
        setCreatedBounties(created.value.bounties)
      }
      if (worked.status === 'fulfilled') {
        const workedB = worked.value.bounties.filter((b) => b.worker === address)
        setClaimedBounties(workedB.filter(b => b.status === 'claimed'))
        setCompletedBounties(workedB.filter(b => b.status === 'closed'))
        setDisputedBounties(workedB.filter(b => b.status === 'disputed'))
      }
    } finally {
      setBountiesLoading(false)
    }
  }, [address])

  useEffect(() => {
    void fetchBounties()
  }, [fetchBounties])

  if (profileLoading) return <FullPageSpinner />

  const sectionStyle: React.CSSProperties = {
    background: 'rgba(10,10,22,0.7)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '1rem',
    padding: '1.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  }

  const completionRate =
    profile &&
    profile.bounties_completed + profile.bounties_disputed > 0
      ? Math.round(
          (profile.bounties_completed /
            (profile.bounties_completed + profile.bounties_disputed)) *
            100,
        )
      : null

  const getDisplayBounties = () => {
    switch (tab) {
      case 'created': return createdBounties
      case 'claimed': return claimedBounties
      case 'completed': return completedBounties
      case 'disputed': return disputedBounties
      default: return []
    }
  }

  const bountiesToDisplay = getDisplayBounties()

  return (
    <div
      className="fade-in"
      style={{
        maxWidth: '800px',
        margin: '0 auto',
        padding: 'clamp(1.5rem, 4vw, 2.5rem) clamp(1rem, 4vw, 1.5rem)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}
    >
      {/* Breadcrumb */}
      <nav style={{ fontSize: '0.875rem', color: '#475569', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <Link href="/" style={{ color: '#6366f1' }}>Marketplace</Link>
        <span>/</span>
        <span>Agents</span>
        <span>/</span>
        <span style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}>{truncateAddress(address)}</span>
      </nav>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1
            style={{
              margin: '0 0 0.5rem',
              fontSize: 'clamp(1.5rem, 4vw, 2rem)',
              fontWeight: 900,
              color: '#f1f5f9',
            }}
          >
            Agent Profile
          </h1>
          <AddressDisplay address={address} />
        </div>
      </div>

      {/* Karma */}
      {profile && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(251,146,60,0.12)', color: '#fb923c', padding: '0.375rem 0.875rem', borderRadius: '9999px', fontSize: '0.9375rem', fontWeight: 600, border: '1px solid rgba(251,146,60,0.3)' }}>
            Karma: ★ {profile.karma}
          </div>
        </div>
      )}

      {/* Bounty tabs */}
      <div style={sectionStyle}>
        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.75rem', overflowX: 'auto' }}>
          {(['created', 'claimed', 'completed', 'disputed'] as Tab[]).map((t) => {
            const count = profile ? (
              t === 'created' ? profile.bounties_created :
              t === 'claimed' ? profile.bounties_claimed :
              t === 'completed' ? profile.bounties_completed :
              t === 'disputed' ? profile.bounties_disputed : 0
            ) : 0;
            return (
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
              {t} {profile && `(${count})`}
            </button>
            )
          })}
        </div>

        {/* Bounty list */}
        {bountiesLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {[...Array(3)].map((_, i) => <SkeletonCard key={i} height="3.5rem" />)}
          </div>
        ) : bountiesToDisplay.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#475569' }}>
            No bounties to display
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {bountiesToDisplay.map((b) => (
              <BountyRow key={b.bounty_id} bounty={b} />
            ))}
          </div>
        )}
      </div>

      {/* Account details */}
      {profile && (
      <div style={sectionStyle}>
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
          Account
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '1rem',
          }}
        >
          {profile?.novice_tier && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.375rem' }}>
                Tier
              </div>
              <Badge variant="hitm">Novice ({profile.novice_count} remaining)</Badge>
            </div>
          )}
          {profile && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.375rem' }}>
                Reputation
              </div>
              <span style={{ color: '#22d3ee', fontWeight: 700, fontSize: '1.125rem' }}>
                {(profile.reputation_score || 0).toFixed(1)}
              </span>
            </div>
          )}
          {completionRate !== null && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.375rem' }}>
                Completion Rate
              </div>
              <span style={{ color: completionRate >= 80 ? '#10b981' : '#f59e0b', fontWeight: 700, fontSize: '1.125rem' }}>
                {completionRate}%
              </span>
            </div>
          )}
          {profile?.avg_review_time && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.375rem' }}>
                Avg Review Time
              </div>
              <span style={{ color: '#94a3b8', fontSize: '0.9375rem' }}>{profile.avg_review_time}</span>
            </div>
          )}
          {profile?.created_at && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.375rem' }}>
                Member Since
              </div>
              <span style={{ color: '#94a3b8', fontSize: '0.9375rem' }}>
                {new Date(profile.created_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </div>
      )}
    </div>
  )
}
