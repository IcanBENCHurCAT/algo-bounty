'use client'

import React, { useEffect, useRef, useState } from 'react'
import { useWallet } from '@txnlab/use-wallet-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

const WALLET_LABELS: Record<string, { label: string; color: string }> = {
  pera:   { label: 'Pera',   color: '#FCD34D' },
  defly:  { label: 'Defly',  color: '#00D4AA' },
  exodus: { label: 'Exodus', color: '#8B5CF6' },
}

function truncate(addr: string): string {
  return `${addr?.slice(0, 6)}…${addr?.slice(-4)}`
}

interface WalletConnectProps {
  variant?: 'full' | 'compact'
}

export function WalletConnect({ variant = 'compact' }: WalletConnectProps) {
  const { wallets } = useWallet()
  const { connected, address, walletType, loading, error, connect, disconnect } = useAuth()
  const [showDropdown, setShowDropdown] = useState(false)
  const [stewardAccepted, setStewardAccepted] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const isDialogOpen = showDropdown && !loading && !(connected && address)

  useEffect(() => {
    if (!isDialogOpen) return

    const dialog = dialogRef.current
    if (!dialog) return

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement && document.activeElement !== document.body
        ? document.activeElement
        : containerRef.current?.querySelector<HTMLButtonElement>('#wallet-connect-btn') ?? null

    dialog.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setShowDropdown(false)
        return
      }
      if (event.key !== 'Tab') return

      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      if (focusable.length === 0) {
        event.preventDefault()
        dialog.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (!dialog.contains(active)) {
        event.preventDefault()
        ;(event.shiftKey ? last : first).focus()
        return
      }

      if (event.shiftKey && (active === first || active === dialog)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      if (previousFocusRef.current?.isConnected) {
        previousFocusRef.current.focus()
      }
    }
  }, [isDialogOpen])

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 1rem',
          borderRadius: '0.625rem',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: '#64748b',
          fontSize: '0.875rem',
        }}
      >
        <span
          aria-hidden="true"
          style={{
            width: '14px',
            height: '14px',
            border: '2px solid #6366f130',
            borderTopColor: '#6366f1',
            borderRadius: '50%',
            animation: 'spin 0.7s linear infinite',
          }}
        />
        Authenticating…
      </div>
    )
  }

  if (connected && address) {
    const walletInfo = walletType ? WALLET_LABELS[walletType] : null
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.375rem 0.75rem',
            borderRadius: '0.625rem',
            background: 'rgba(16,185,129,0.08)',
            border: '1px solid rgba(16,185,129,0.25)',
            color: '#10b981',
            fontSize: '0.8125rem',
            fontWeight: 600,
            fontFamily: 'monospace',
          }}
        >
          {walletInfo && (
            <span
              aria-hidden="true"
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: walletInfo.color,
                flexShrink: 0,
              }}
            />
          )}
          {truncate(address)}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void disconnect()}
          style={{ color: '#64748b', fontSize: '0.8125rem' }}
        >
          Disconnect
        </Button>
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      {error && (
        <div
          role="alert"
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 8px)',
            right: 0,
            background: 'rgba(239,68,68,0.12)',
            border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: '0.5rem',
            padding: '0.5rem 0.75rem',
            fontSize: '0.75rem',
            color: '#f87171',
            whiteSpace: 'nowrap',
            zIndex: 10,
          }}
        >
          {error}
        </div>
      )}
      <Button
        type="button"
        variant="primary"
        size="sm"
        onClick={() => setShowDropdown((v) => !v)}
        id="wallet-connect-btn"
        aria-haspopup="dialog"
        aria-expanded={showDropdown}
        aria-controls={showDropdown ? 'wallet-connect-dialog' : undefined}
      >
        Connect Wallet
      </Button>

      {showDropdown && (
        <>
          <div
            aria-hidden="true"
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 40,
            }}
            onClick={() => setShowDropdown(false)}
          />
          <div
            ref={dialogRef}
            id="wallet-connect-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="wallet-connect-dialog-title"
            tabIndex={-1}
            style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: 0,
              background: 'rgba(10,10,20,0.98)',
              backdropFilter: 'blur(24px)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '0.875rem',
              padding: '0.5rem',
              minWidth: '240px',
              zIndex: 50,
              boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
              outline: 'none',
            }}
          >
            <div
              style={{
                padding: '0.5rem 0.75rem',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
                marginBottom: '0.5rem',
              }}
            >
              <label style={{ display: 'flex', gap: '0.5rem', cursor: 'pointer', alignItems: 'flex-start' }}>
                <input
                  id="agent-steward-checkbox"
                  type="checkbox"
                  checked={stewardAccepted}
                  onChange={(e) => setStewardAccepted(e.target.checked)}
                  style={{ marginTop: '0.15rem', cursor: 'pointer' }}
                />
                <span style={{ fontSize: '0.7rem', color: '#94a3b8', lineHeight: '1.3' }}>
                  I agree that any wallet controlled by an autonomous software agent must have a designated human steward who accepts full legal, tax, and financial responsibility.
                </span>
              </label>
            </div>

            <p
              id="wallet-connect-dialog-title"
              style={{
                margin: '0 0 0.5rem',
                padding: '0.5rem 0.75rem',
                fontSize: '0.75rem',
                color: '#64748b',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}
            >
              Choose Wallet
            </p>
            {wallets.map((wallet) => {
              const info = WALLET_LABELS[wallet.id]
              if (!info) return null
              return (
                <button
                  key={wallet.id}
                  type="button"
                  id={`connect-${wallet.id}`}
                  disabled={!stewardAccepted}
                  onClick={() => {
                    if (!stewardAccepted) return
                    setShowDropdown(false)
                    void connect(wallet.id)
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    width: '100%',
                    padding: '0.625rem 0.875rem',
                    borderRadius: '0.625rem',
                    background: 'transparent',
                    border: 'none',
                    color: stewardAccepted ? '#e2e8f0' : '#64748b',
                    cursor: stewardAccepted ? 'pointer' : 'not-allowed',
                    opacity: stewardAccepted ? 1 : 0.5,
                    fontSize: '0.9375rem',
                    fontWeight: 500,
                    textAlign: 'left',
                    transition: 'background 0.15s',
                    fontFamily: 'inherit',
                  }}
                  onMouseEnter={(e) => {
                    if (stewardAccepted) {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (stewardAccepted) {
                      e.currentTarget.style.background = 'transparent'
                    }
                  }}
                >
                  <span
                    aria-hidden="true"
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      background: info.color,
                      flexShrink: 0,
                    }}
                  />
                  {info.label}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
