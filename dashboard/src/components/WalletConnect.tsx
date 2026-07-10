'use client'

import React, { useState } from 'react'
import { useWallet, WalletId } from '@txnlab/use-wallet-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'

const WALLET_LABELS: Record<string, { label: string; color: string }> = {
  [WalletId.PERA]:   { label: 'Pera',   color: '#FCD34D' },
  [WalletId.DEFLY]:  { label: 'Defly',  color: '#00D4AA' },
  [WalletId.EXODUS]: { label: 'Exodus', color: '#8B5CF6' },
}

function truncate(addr: string): string {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`
}

interface WalletConnectProps {
  variant?: 'full' | 'compact'
}

export function WalletConnect({ variant = 'compact' }: WalletConnectProps) {
  const { wallets } = useWallet()
  const { connected, address, walletType, loading, error, connect, disconnect } = useAuth()
  const [showDropdown, setShowDropdown] = useState(false)

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
    <div style={{ position: 'relative' }}>
      {error && (
        <div
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
        variant="primary"
        size="sm"
        onClick={() => setShowDropdown((v) => !v)}
        id="wallet-connect-btn"
      >
        Connect Wallet
      </Button>

      {showDropdown && (
        <>
          <div
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 40,
            }}
            onClick={() => setShowDropdown(false)}
          />
          <div
            style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: 0,
              background: 'rgba(10,10,20,0.98)',
              backdropFilter: 'blur(24px)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '0.875rem',
              padding: '0.5rem',
              minWidth: '200px',
              zIndex: 50,
              boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
            }}
          >
            <p
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
                  id={`connect-${wallet.id}`}
                  onClick={() => {
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
                    color: '#e2e8f0',
                    cursor: 'pointer',
                    fontSize: '0.9375rem',
                    fontWeight: 500,
                    textAlign: 'left',
                    transition: 'background 0.15s',
                    fontFamily: 'inherit',
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = 'transparent')
                  }
                >
                  <span
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
