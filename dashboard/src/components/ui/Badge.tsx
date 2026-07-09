import React from 'react'

type BadgeVariant = 'open' | 'claimed' | 'submitted' | 'approved' | 'disputed' | 'refunded' | 'closed' | 'hitm' | 'novice' | 'default'

const VARIANT_STYLES: Record<BadgeVariant, { bg: string; color: string; dot: string }> = {
  open:      { bg: 'rgba(16,185,129,0.12)', color: '#10b981', dot: '#10b981' },
  claimed:   { bg: 'rgba(99,102,241,0.12)', color: '#818cf8', dot: '#818cf8' },
  submitted: { bg: 'rgba(245,158,11,0.12)', color: '#fbbf24', dot: '#fbbf24' },
  approved:  { bg: 'rgba(16,185,129,0.18)', color: '#34d399', dot: '#34d399' },
  disputed:  { bg: 'rgba(239,68,68,0.12)',  color: '#f87171', dot: '#f87171' },
  refunded:  { bg: 'rgba(148,163,184,0.12)',color: '#94a3b8', dot: '#94a3b8' },
  closed:    { bg: 'rgba(148,163,184,0.12)',color: '#64748b', dot: '#64748b' },
  hitm:      { bg: 'rgba(251,146,60,0.12)', color: '#fb923c', dot: '#fb923c' },
  novice:    { bg: 'rgba(99,102,241,0.12)', color: '#a78bfa', dot: '#a78bfa' },
  default:   { bg: 'rgba(100,116,139,0.12)',color: '#94a3b8', dot: '#94a3b8' },
}

interface BadgeProps {
  variant?: BadgeVariant
  children: React.ReactNode
  showDot?: boolean
  className?: string
}

export function Badge({ variant = 'default', children, showDot = false }: BadgeProps) {
  const s = VARIANT_STYLES[variant] ?? VARIANT_STYLES.default
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.375rem',
        padding: '0.25rem 0.625rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        letterSpacing: '0.025em',
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.color}30`,
        whiteSpace: 'nowrap',
      }}
    >
      {showDot && (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: s.dot,
            flexShrink: 0,
          }}
        />
      )}
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const variant = (status.toLowerCase()) as BadgeVariant
  return (
    <Badge variant={variant} showDot>
      {status.toUpperCase()}
    </Badge>
  )
}
