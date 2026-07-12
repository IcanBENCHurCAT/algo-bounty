'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/providers'
import { getMyProfile, getBounties } from '@/lib/api'
import type { AgentProfile, Bounty } from '@/types'
import { Button } from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import { Badge } from '@/components/ui/Badge'
import { SkeletonLine, SkeletonCard } from '@/components/ui/Skeleton'



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


// ─── Page ─────────────────────────────────────────────────────────────────────

type Tab = 'created' | 'claimed' | 'completed' | 'disputed'

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
  }, [connected, address, tab])

  const handleRefresh = async () => {
    await refreshProfile()
    toast.info('Profile refreshed')
  }

  const handleDisconnect = async () => {
    await disconnect()
    toast.info('Wallet disconnected')
  }

  // ─── Not connected ─────────────────────────────────────────────────────

  if (!connected || !address) {
    return (
      <div
        className="fade-in"
        style={{
          maxWidth: '600px',
          margin: '4rem auto',
          padding: '0 1.5rem',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            padding: '3rem',
            background: 'rgba(99,102,241,0.06)',
            border: '1px solid rgba(99,102,241,0.15)',
            borderRadius: '1.25rem',
          }}
        >
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>👤</div>
          <h1
            style={{
              fontSize: '1.5rem',
              fontWeight: 800,
              color: '#f1f5f9',
              marginBottom: '0.75rem',
            }}
          >
            No Wallet Connected
          </h1>
          <p style={{ color: '#64748b', marginBottom: '1.5rem' }}>
            Connect your wallet to view your AlgoBounty profile.
          </p>

        </div>
      </div>
    )
  }

  // ─── Loading ───────────────────────────────────────────────────────────

  if (loading && !profile) {
    return (
      <div
        style={{
          maxWidth: '800px',
          margin: '0 auto',
          padding: 'clamp(1.5rem, 4vw, 2.5rem) clamp(1rem, 4vw, 1.5rem)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.5rem',
        }}
      >
        <SkeletonLine width="40%" height="2rem" />
        <SkeletonCard />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '1rem' }}>
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} height="5rem" />)}
        </div>
      </div>
    )
  }

  // ─── Profile loaded ────────────────────────────────────────────────────

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
    profile && profile.bounties_completed + profile.bounties_disputed > 0
      ? Math.round(
          (profile.bounties_completed /
            (profile.bounties_completed + profile.bounties_disputed)) *
            100,
        )
      : null

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
            My Profile
          </h1>
          <AddressDisplay address={address} />
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Button
            id="refresh-profile-btn"
            variant="ghost"
            size="sm"
            onClick={() => void handleRefresh()}
          >
            ↻ Refresh
          </Button>
          <Button
            id="disconnect-btn"
            variant="danger"
            size="sm"
            onClick={() => void handleDisconnect()}
          >
            Disconnect
          </Button>
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

      {/* Quick links */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <Link href="/create">
          <Button>+ Create Bounty</Button>
        </Link>
        <Link href={`/agents/${address}`}>
          <Button variant="ghost">Public Profile</Button>
        </Link>
      </div>
    </div>
  )
}
