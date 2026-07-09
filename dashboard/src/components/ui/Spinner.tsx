import React from 'react'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  color?: string
}

const SIZES = { sm: '1rem', md: '1.5rem', lg: '2.5rem' }

export function Spinner({ size = 'md', color = '#6366f1' }: SpinnerProps) {
  const px = SIZES[size]
  return (
    <span
      role="status"
      aria-label="Loading"
      style={{
        display: 'inline-block',
        width: px,
        height: px,
        border: `2px solid ${color}30`,
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
        flexShrink: 0,
      }}
    />
  )
}

export function FullPageSpinner() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        flexDirection: 'column',
        gap: '1rem',
        color: '#64748b',
      }}
    >
      <Spinner size="lg" />
      <span style={{ fontSize: '0.875rem' }}>Loading…</span>
    </div>
  )
}
