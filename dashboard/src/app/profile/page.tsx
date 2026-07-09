'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/providers'
import { getMyProfile } from '@/lib/api'
import type { AgentProfile } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { SkeletonLine, SkeletonCard } from '@/components/ui/Skeleton'

// ─── Stat card ────────────────────────────────────────────────────────────────

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
        {address.slice(0, 20)}…{address.slice(-8)}
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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
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
  }, [connected, jwt])

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
          <Link href="/">
            <Button>← Back to Marketplace</Button>
          </Link>
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

      {/* Karma + Reputation */}
      {profile && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '1rem' }}>
          <StatCard label="Karma" value={`★ ${profile.karma}`} accent="#818cf8" />
          <StatCard
            label="Reputation Score"
            value={profile.reputation_score.toFixed(1)}
            accent="#22d3ee"
          />
          <StatCard
            label="Bounties Created"
            value={profile.bounties_created}
            accent="#10b981"
          />
          <StatCard
            label="Bounties Claimed"
            value={profile.bounties_claimed}
            accent="#6366f1"
          />
          <StatCard
            label="Completed"
            value={profile.bounties_completed}
            accent="#10b981"
          />
          <StatCard
            label="Disputed"
            value={profile.bounties_disputed}
            accent="#ef4444"
          />
        </div>
      )}

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
        <Link href="/">
          <Button variant="ghost">View Marketplace</Button>
        </Link>
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
