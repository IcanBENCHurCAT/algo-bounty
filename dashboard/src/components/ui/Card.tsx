import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  style?: React.CSSProperties
  glow?: boolean
  hoverable?: boolean
  onClick?: () => void
}

export function Card({ children, style, glow = false, hoverable = false, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'rgba(15, 15, 30, 0.7)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '1rem',
        padding: '1.5rem',
        transition: 'all 0.2s ease',
        cursor: onClick ? 'pointer' : undefined,
        ...(glow ? { boxShadow: '0 0 40px rgba(99,102,241,0.08), 0 8px 32px rgba(0,0,0,0.4)' } : { boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }),
        ...(hoverable ? {
          transition: 'all 0.2s ease',
        } : {}),
        ...style,
      }}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        marginBottom: '1rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

export function CardTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3
      style={{
        margin: 0,
        fontSize: '1.125rem',
        fontWeight: 700,
        color: '#f1f5f9',
      }}
    >
      {children}
    </h3>
  )
}
