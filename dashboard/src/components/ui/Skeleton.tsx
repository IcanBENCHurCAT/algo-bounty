import React from 'react'

interface SkeletonProps {
  width?: string
  height?: string
  borderRadius?: string
  style?: React.CSSProperties
}

export function Skeleton({
  width = '100%',
  height = '1rem',
  borderRadius = '0.375rem',
  style,
}: SkeletonProps) {
  return (
    <span
      style={{
        display: 'block',
        width,
        height,
        borderRadius,
        background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
        backgroundSize: '400% 100%',
        animation: 'shimmer 1.5s ease infinite',
        ...style,
      }}
    />
  )
}

export function BountyCardSkeleton() {
  return (
    <div
      style={{
        background: 'rgba(15,15,30,0.7)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '1rem',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.875rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Skeleton width="80px" height="22px" borderRadius="9999px" />
        <Skeleton width="60px" height="16px" />
      </div>
      <Skeleton width="40%" height="12px" />
      <Skeleton height="14px" />
      <Skeleton width="85%" height="14px" />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
        <Skeleton width="70px" height="24px" borderRadius="0.5rem" />
        <Skeleton width="90px" height="14px" />
      </div>
    </div>
  )
}
