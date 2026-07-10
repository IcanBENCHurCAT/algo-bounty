'use client'

import React from 'react'
import Link from 'next/link'
import type { Bounty, BountyStatus } from '@/types'
import { StatusBadge, Badge } from '@/components/ui/Badge'

const STATUS_COLORS: Record<BountyStatus, string> = {
  open:      '#10b981',
  claimed:   '#818cf8',
  submitted: '#fbbf24',
  approved:  '#34d399',
  disputed:  '#f87171',
  refunded:  '#94a3b8',
  closed:    '#64748b',
}

function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

function formatAlgo(microAlgo: number): string {
  const algo = microAlgo / 1_000_000
  if (algo >= 1000) return `${(algo / 1000).toFixed(1)}K ALGO`
  return `${algo % 1 === 0 ? algo.toFixed(0) : algo.toFixed(2)} ALGO`
}

function getRepoHostname(url: string | null): string | null {
  if (!url) return null
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch {
    return null
  }
}

interface BountyCardProps {
  bounty: Bounty
}

export function BountyCard({ bounty }: BountyCardProps) {
  const accentColor = STATUS_COLORS[bounty.status] ?? '#64748b'
  const hostname = getRepoHostname(bounty.repo_url)
  const displayTags = bounty.tags?.slice(0, 3) || []
  const remainingDays =
    bounty.deadline_rounds_remaining != null
      ? Math.ceil(bounty.deadline_rounds_remaining / 30 / 24 / 60 * 4.5) // ~4.5s per block
      : null

  return (
    <Link
      href={`/bounties/${bounty.bounty_id}`}
      style={{ textDecoration: 'none', display: 'block' }}
    >
      <div
        className="bounty-card"
        style={{
          background: 'rgba(12,12,24,0.8)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: '1rem',
          padding: '1.375rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.875rem',
          transition: 'all 0.2s ease',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Accent top border */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: `linear-gradient(90deg, ${accentColor}80, transparent)`,
            borderRadius: '1rem 1rem 0 0',
          }}
        />

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
          <StatusBadge status={bounty.status} />
          <span style={{ fontSize: '0.75rem', color: '#475569', flexShrink: 0 }}>
            {formatTimeAgo(bounty.created_at)}
          </span>
        </div>

        {/* ID */}
        <span style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: '#475569', letterSpacing: '0.05em' }}>
          {bounty.bounty_id}
        </span>

        {/* Description */}
        <p
          style={{
            margin: 0,
            fontSize: '0.9375rem',
            fontWeight: 600,
            color: '#cbd5e1',
            lineHeight: 1.5,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {bounty.description}
        </p>

        {/* Amount + HITM row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: '1.25rem',
              fontWeight: 800,
              color: '#22d3ee',
              letterSpacing: '-0.025em',
            }}
          >
            {formatAlgo(bounty.amount)}
          </span>
          {bounty.hitm && <Badge variant="hitm">HITM</Badge>}
          {bounty.karma_required > 0 && (
            <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              ★ {bounty.karma_required}+ karma
            </span>
          )}
        </div>

        {/* Repo + deadline row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
          {hostname && (
            <span
              style={{
                fontSize: '0.75rem',
                color: '#475569',
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
              </svg>
              {hostname}
            </span>
          )}
          {remainingDays != null && remainingDays > 0 && (
            <span style={{ fontSize: '0.75rem', color: remainingDays <= 2 ? '#f87171' : '#64748b', flexShrink: 0 }}>
              {remainingDays}d left
            </span>
          )}
        </div>

        {/* Tags */}
        {displayTags.length > 0 && (
          <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap' }}>
            {displayTags.map((tag) => (
              <span
                key={tag}
                style={{
                  fontSize: '0.6875rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '0.375rem',
                  background: 'rgba(99,102,241,0.1)',
                  color: '#818cf8',
                  border: '1px solid rgba(99,102,241,0.2)',
                  fontWeight: 500,
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  )
}
