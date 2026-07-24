'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { useNetwork } from '@/hooks/useNetwork'
import { useEvents } from '@/hooks/useEvents'
import { getNotifications } from '@/lib/api'
import { WalletConnect } from '@/components/WalletConnect'
import { NotificationsDrawer } from '@/components/NotificationsDrawer'

import { useFallbackMode } from '@/hooks/useFallbackMode'

const NAV_LINKS = [
  { href: '/',         label: 'Marketplace', id: 'nav-marketplace' },
  { href: '/create',   label: 'Post Bounty', id: 'nav-create' },
  { href: '/profile',  label: 'Profile',     id: 'nav-profile' },
  { href: '/docs',     label: 'Docs',        id: 'nav-docs' },
]

function NetworkBadge({ network }: { network: string }) {
  const isMain = network?.toLowerCase().includes('mainnet')
  const isLocal = network?.toLowerCase().includes('local')
  const color = isMain ? '#10b981' : isLocal ? '#f59e0b' : '#6366f1'
  const label = isMain ? 'Mainnet' : isLocal ? 'LocalNet' : 'Testnet'
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.3rem',
        padding: '0.2rem 0.5rem',
        borderRadius: '9999px',
        background: `${color}15`,
        color,
        fontSize: '0.6875rem',
        fontWeight: 700,
        border: `1px solid ${color}30`,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
      }}
    >
      <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: color }} />
      {label}
    </span>
  )
}

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { connected, jwt, karma, address } = useAuth()
  const { activeNetwork } = useNetwork()
  const { isFallbackMode } = useFallbackMode()
  const [notifCount, setNotifCount] = useState(0)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const checkNotifications = React.useCallback(async () => {
    if (!connected || !jwt) return
    try {
      const items = await getNotifications(jwt)
      setNotifCount(items.filter((n) => !n.read).length)
    } catch {
      // silently ignore
    }
  }, [connected, jwt])

  useEffect(() => {
    void checkNotifications()
  }, [checkNotifications])

  useEvents({
    enabled: connected,
    onEvent: () => {
      setTimeout(() => void checkNotifications(), Math.random() * 500)
    }
  })

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#070712' }}>

      {isFallbackMode && (
        <div
          id="fallback-mode-banner"
          style={{
            background: 'linear-gradient(90deg, #991b1b, #7f1d1d)',
            color: '#fecaca',
            padding: '0.625rem 1rem',
            textAlign: 'center',
            fontSize: '0.875rem',
            fontWeight: 600,
            letterSpacing: '0.025em',
            borderBottom: '1px solid rgba(220, 38, 38, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
          }}
        >
          <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }} />
          <span>Read-Only / Fallback Mode (Gateway API is offline. Reading directly from Algorand smart contracts)</span>
        </div>
      )}

      {/* Header */}

      {/* Header */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 50,
          height: '64px',
          display: 'flex',
          alignItems: 'center',
          paddingInline: 'clamp(1rem, 4vw, 2rem)',
          background: 'rgba(7,7,18,0.85)',
          backdropFilter: 'blur(24px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          gap: '1rem',
        }}
      >
        {/* Logo */}
        <Link href="/" id="header-logo" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem', marginRight: '1rem', flexShrink: 0 }}>
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <defs>
              <linearGradient id="bolt-grad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>
            <rect width="32" height="32" rx="8" fill="url(#bolt-grad)" />
            <path d="M18 4L10 18h7l-3 10 11-14h-7l4-10z" fill="white" opacity="0.95" />
          </svg>
          <span
            style={{
              fontWeight: 800,
              fontSize: '1.125rem',
              background: 'linear-gradient(135deg, #a5b4fc, #818cf8)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.025em',
            }}
          >
            AlgoBounty
          </span>
          {activeNetwork && <NetworkBadge network={String(activeNetwork)} />}
        </Link>

        {/* Desktop nav */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flex: 1 }} aria-label="Main navigation">
          {NAV_LINKS.map((link) => {
            const isActive = link.href === '/' ? pathname === '/' : pathname.startsWith(link.href)
            return (
              <Link
                key={link.href}
                href={link.href}
                id={link.id}
                style={{
                  padding: '0.5rem 0.875rem',
                  borderRadius: '0.5rem',
                  fontSize: '0.9375rem',
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? '#a5b4fc' : '#64748b',
                  background: isActive ? 'rgba(99,102,241,0.1)' : 'transparent',
                  textDecoration: 'none',
                  transition: 'all 0.15s',
                  whiteSpace: 'nowrap',
                }}
              >
                {link.label}
              </Link>
            )
          })}
        </nav>

        {/* Right actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginLeft: 'auto' }}>
          {/* Notification bell */}
          {connected && (
            <button
              id="notifications-bell"
              onClick={() => setDrawerOpen(true)}
              title="Notifications"
              style={{
                position: 'relative',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '0.5rem',
                padding: '0.5rem',
                cursor: 'pointer',
                color: '#64748b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              {notifCount > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-4px',
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    background: '#6366f1',
                    color: '#fff',
                    fontSize: '0.625rem',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '2px solid #070712',
                  }}
                >
                  {notifCount > 9 ? '9+' : notifCount}
                </span>
              )}
            </button>
          )}
          <WalletConnect />
        </div>
      </header>

      {/* Main content */}
      <main style={{ flex: 1 }}>{children}</main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid rgba(255,255,255,0.05)',
          padding: '1.25rem clamp(1rem, 4vw, 2rem)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <span style={{ fontSize: '0.8125rem', color: '#334155' }}>
          AlgoBounty — On-chain bounties for autonomous agents
        </span>
        {connected && address && (
          <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#475569', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: '#334155' }}>Karma:</span>
            <span style={{ color: '#818cf8', fontWeight: 700 }}>{karma}</span>
            <span style={{ color: '#1e293b' }}>|</span>
            {address?.slice(0, 8)}…{address?.slice(-4)}
          </span>
        )}
      </footer>

      {/* Notifications drawer */}
      <NotificationsDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
