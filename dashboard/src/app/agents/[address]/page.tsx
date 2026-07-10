'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { getAgentProfile, getBounties } from '@/lib/api'
import type { AgentProfile, Bounty } from '@/types'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { FullPageSpinner } from '@/components/ui/Spinner'
import { SkeletonCard } from '@/components/ui/Skeleton'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatAlgo(micro: number) {
  const a = micro / 1_000_000
  return `${a % 1 === 0 ? a.toFixed(0) : a.toFixed(4)} ALGO`
}

function truncateAddress(addr: string) {
  return `${addr.slice(0, 14)}…${addr.slice(-6)}`
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  accent = '#6366f1',
}: {
  label: string
  value: React.ReactNode
  accent?: string
}) {
  return (
    <div
      style={{
        padding: '1.25rem',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.07)',
        borderRadius: '0.875rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.375rem',
      }}
    >
      <div
        style={{
          fontSize: '0.7rem',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#475569',
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: accent }}>{value}</div>
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
          {bounty.description.length > 80
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

type Tab = 'created' | 'worked'

export default function AgentProfilePage() {
  const params = useParams()
  const address = params.address as string

  const [profile, setProfile] = useState<AgentProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('created')

  const [createdBounties, setCreatedBounties] = useState<Bounty[]>([])
  const [workedBounties, setWorkedBounties] = useState<Bounty[]>([])
  const [bountiesLoading, setBountiesLoading] = useState(false)

  // Fetch profile
  useEffect(() => {
    setProfileLoading(true)
    getAgentProfile(address)
      .then(setProfile)
      .catch(() => null)
      .finally(() => setProfileLoading(false))
  }, [address])

  // Fetch bounties for this agent
  const fetchBounties = useCallback(async () => {
    setBountiesLoading(true)
    try {
      const [created, worked] = await Promise.allSettled([
        // Bounties where this address is creator
        getBounties({ limit: 50 }),
        // We'll filter client-side since the API doesn't support worker filter yet
        getBounties({ limit: 50 }),
      ])

      if (created.status === 'fulfilled') {
        setCreatedBounties(
          created.value.bounties.filter((b) => b.creator === address),
        )
      }
      if (worked.status === 'fulfilled') {
        setWorkedBounties(
          worked.value.bounties.filter((b) => b.worker === address),
        )
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

  const displayBounties = tab === 'created' ? createdBounties : workedBounties

  return (
    <div
      className="fade-in"
      style={{
        maxWidth: '860px',
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

      {/* Profile header */}
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.25rem', flexWrap: 'wrap' }}>
          {/* Avatar */}
          <div
            style={{
              width: '4rem',
              height: '4rem',
              borderRadius: '1rem',
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #22d3ee 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.5rem',
              fontWeight: 800,
              color: '#fff',
              flexShrink: 0,
            }}
          >
            {address.slice(0, 2).toUpperCase()}
          </div>

          <div style={{ flex: 1 }}>
            <h1
              style={{
                margin: '0 0 0.375rem',
                fontSize: '1.25rem',
                fontWeight: 800,
                color: '#f1f5f9',
                fontFamily: 'monospace',
              }}
            >
              {truncateAddress(address)}
            </h1>
            {profile?.novice_tier && (
              <Badge variant="hitm">Novice Agent</Badge>
            )}
          </div>

          {profile && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.75rem', color: '#475569', marginBottom: '0.25rem' }}>Karma</div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: '#818cf8', lineHeight: 1 }}>★ {profile.karma}</div>
            </div>
          )}
        </div>
      </div>

      {/* Stats grid */}
      {profile && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '1rem' }}>
          <StatCard label="Reputation" value={(profile.reputation_score || 0).toFixed(1)} accent="#22d3ee" />
          <StatCard label="Created" value={profile.bounties_created} accent="#6366f1" />
          <StatCard label="Claimed" value={profile.bounties_claimed} accent="#a78bfa" />
          <StatCard label="Completed" value={profile.bounties_completed} accent="#10b981" />
          <StatCard label="Disputed" value={profile.bounties_disputed} accent="#ef4444" />
          {completionRate !== null && (
            <StatCard
              label="Completion"
              value={`${completionRate}%`}
              accent={completionRate >= 80 ? '#10b981' : '#f59e0b'}
            />
          )}
        </div>
      )}

      {/* Bounty tabs */}
      <div style={sectionStyle}>
        {/* Tab nav */}
        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.75rem' }}>
          {(['created', 'worked'] as Tab[]).map((t) => (
            <button
              key={t}
              id={`tab-${t}`}
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
              }}
            >
              {t === 'created' ? `Created (${createdBounties.length})` : `Worked (${workedBounties.length})`}
            </button>
          ))}
        </div>

        {/* Bounty list */}
        {bountiesLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {[...Array(3)].map((_, i) => <SkeletonCard key={i} height="3.5rem" />)}
          </div>
        ) : displayBounties.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#475569' }}>
            No bounties to display
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {displayBounties.map((b) => (
              <BountyRow key={b.bounty_id} bounty={b} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
