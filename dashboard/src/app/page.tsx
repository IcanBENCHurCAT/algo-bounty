'use client'

import React, { useCallback, useState } from 'react'
import { useBounties } from '@/hooks/useBounties'
import { useEvents } from '@/hooks/useEvents'
import { BountyCard } from '@/components/BountyCard'
import { Button } from '@/components/ui/Button'
import { BountyCardSkeleton } from '@/components/ui/Skeleton'
import type { BountyFilters, SseEvent } from '@/types'

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'open', label: 'Open' },
  { value: 'claimed', label: 'Claimed' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'approved', label: 'Approved' },
  { value: 'disputed', label: 'Disputed' },
  { value: 'refunded', label: 'Refunded' },
  { value: 'closed', label: 'Closed' },
]

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Newest' },
  { value: 'amount',     label: 'Highest Reward' },
  { value: 'karma_required', label: 'Karma Required' },
  { value: 'deadline',   label: 'Deadline' },
]

const DEFAULT_FILTERS: BountyFilters = {
  status: 'open',
  hitm: 'any',
  sortBy: 'created_at',
}

export default function MarketplacePage() {
  const [filters, setFilters] = useState<BountyFilters>(DEFAULT_FILTERS)
  const [pendingFilters, setPendingFilters] = useState<BountyFilters>(DEFAULT_FILTERS)

  const { bounties, loading, error, hasMore, total, loadMore, refresh } = useBounties(filters)

  // Real-time updates: refresh on any bounty event
  const handleSseEvent = useCallback(
    (event: SseEvent) => {
      if (event.type.startsWith('bounty.')) {
        refresh()
      }
    },
    [refresh],
  )
  useEvents({ onEvent: handleSseEvent })

  const applyFilters = () => setFilters({ ...pendingFilters })
  const resetFilters = () => {
    setPendingFilters(DEFAULT_FILTERS)
    setFilters(DEFAULT_FILTERS)
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.5rem 0.75rem',
    borderRadius: '0.5rem',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    color: '#e2e8f0',
    fontSize: '0.875rem',
    fontFamily: 'inherit',
    outline: 'none',
    transition: 'border-color 0.15s',
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: '#64748b',
    marginBottom: '0.375rem',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
  }

  return (
    <div
      style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: 'clamp(1.5rem, 4vw, 2.5rem) clamp(1rem, 4vw, 2rem)',
        display: 'grid',
        gridTemplateColumns: '260px 1fr',
        gap: '2rem',
        alignItems: 'start',
      }}
    >
      {/* ── Filters sidebar ── */}
      <aside
        className="fade-in"
        style={{
          position: 'sticky',
          top: '80px',
          background: 'rgba(10,10,22,0.8)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: '1rem',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}
      >
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>Filters</h2>

        {/* Status */}
        <div>
          <label style={labelStyle}>Status</label>
          <select
            id="filter-status"
            value={pendingFilters.status ?? ''}
            onChange={(e) => setPendingFilters((f) => ({ ...f, status: e.target.value }))}
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* HITM */}
        <div>
          <label style={labelStyle}>HITM Mode</label>
          <select
            id="filter-hitm"
            value={pendingFilters.hitm ?? 'any'}
            onChange={(e) => setPendingFilters((f) => ({ ...f, hitm: e.target.value as BountyFilters['hitm'] }))}
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            <option value="any">Any</option>
            <option value="true">HITM Only</option>
            <option value="false">Trustless Only</option>
          </select>
        </div>

        {/* Sort */}
        <div>
          <label style={labelStyle}>Sort By</label>
          <select
            id="filter-sort"
            value={pendingFilters.sortBy ?? 'created_at'}
            onChange={(e) => setPendingFilters((f) => ({ ...f, sortBy: e.target.value as BountyFilters['sortBy'] }))}
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Amount range */}
        <div>
          <label style={labelStyle}>Min ALGO</label>
          <input
            id="filter-min-amount"
            type="number"
            min={0}
            placeholder="0"
            value={pendingFilters.minAmount ?? ''}
            onChange={(e) => setPendingFilters((f) => ({ ...f, minAmount: e.target.value ? Number(e.target.value) : undefined }))}
            style={inputStyle}
          />
        </div>
        <div>
          <label style={labelStyle}>Max ALGO</label>
          <input
            id="filter-max-amount"
            type="number"
            min={0}
            placeholder="Any"
            value={pendingFilters.maxAmount ?? ''}
            onChange={(e) => setPendingFilters((f) => ({ ...f, maxAmount: e.target.value ? Number(e.target.value) : undefined }))}
            style={inputStyle}
          />
        </div>

        {/* Repo search */}
        <div>
          <label style={labelStyle}>Repository</label>
          <input
            id="filter-repo"
            type="text"
            placeholder="github.com/…"
            value={pendingFilters.repo ?? ''}
            onChange={(e) => setPendingFilters((f) => ({ ...f, repo: e.target.value || undefined }))}
            style={inputStyle}
          />
        </div>

        {/* Min karma */}
        <div>
          <label style={labelStyle}>Max Karma Req.</label>
          <input
            id="filter-min-karma"
            type="number"
            min={0}
            placeholder="Any"
            value={pendingFilters.minKarma ?? ''}
            onChange={(e) => setPendingFilters((f) => ({ ...f, minKarma: e.target.value ? Number(e.target.value) : undefined }))}
            style={inputStyle}
          />
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
          <Button id="apply-filters" fullWidth onClick={applyFilters} size="sm">Apply</Button>
          <Button id="reset-filters" variant="ghost" size="sm" onClick={resetFilters} style={{ flexShrink: 0 }}>Reset</Button>
        </div>
      </aside>

      {/* ── Bounty grid ── */}
      <div>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 'clamp(1.5rem, 3vw, 2rem)', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.025em' }}>
              Bounty Marketplace
            </h1>
            {!loading && (
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#475569' }}>
                {total} bount{total !== 1 ? 'ies' : 'y'} available
              </p>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div
            className="fade-in"
            style={{
              padding: '1rem 1.25rem',
              borderRadius: '0.75rem',
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.2)',
              color: '#f87171',
              marginBottom: '1.5rem',
              fontSize: '0.9375rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
            }}
          >
            <span>{error}</span>
            <Button variant="danger" size="sm" onClick={refresh}>Retry</Button>
          </div>
        )}

        {/* Skeleton loading */}
        {loading && bounties.length === 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
            {Array.from({ length: 6 }).map((_, i) => <BountyCardSkeleton key={i} />)}
          </div>
        )}

        {/* Empty state */}
        {!loading && bounties.length === 0 && !error && (
          <div
            className="fade-in"
            style={{
              textAlign: 'center',
              padding: '5rem 2rem',
              color: '#475569',
            }}
          >
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎯</div>
            <h3 style={{ color: '#64748b', margin: '0 0 0.5rem', fontWeight: 600 }}>No bounties found</h3>
            <p style={{ fontSize: '0.9375rem' }}>Try adjusting your filters or check back later.</p>
          </div>
        )}

        {/* Bounty cards grid */}
        {bounties.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
            {bounties.map((bounty) => <BountyCard key={bounty.bounty_id} bounty={bounty} />)}
          </div>
        )}

        {/* Load more */}
        {hasMore && (
          <div style={{ marginTop: '2rem', textAlign: 'center' }}>
            <Button
              id="load-more-btn"
              variant="secondary"
              loading={loading && bounties.length > 0}
              onClick={loadMore}
            >
              Load More
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}