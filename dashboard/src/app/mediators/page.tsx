'use client'

import React, { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/providers'
import {
  getEvaluators,
  getMyEvaluatorStatus,
  registerEvaluator,
  deregisterEvaluator,
  Evaluator,
  EvaluatorStatusResponse,
} from '@/lib/api'

export default function MediatorsPage() {
  const { connected, jwt, address } = useAuth()
  const toast = useToast()

  const [arbitrators, setArbitrators] = useState<Evaluator[]>([])
  const [status, setStatus] = useState<EvaluatorStatusResponse | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [loadingList, setLoadingList] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetchList()
  }, [])

  useEffect(() => {
    if (connected && jwt) {
      fetchStatus()
    } else {
      setStatus(null)
      setLoadingStatus(false)
    }
  }, [connected, jwt])

  async function fetchList() {
    setLoadingList(true)
    try {
      const data = await getEvaluators()
      setArbitrators(data)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load active mediators')
    } finally {
      setLoadingList(false)
    }
  }

  async function fetchStatus() {
    if (!jwt) return
    setLoadingStatus(true)
    try {
      const data = await getMyEvaluatorStatus(jwt)
      setStatus(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingStatus(false)
    }
  }

  async function handleRegister() {
    if (!jwt) return
    setActionLoading(true)
    try {
      await registerEvaluator(jwt)
      toast.success('Successfully registered as a Mediator!')
      await fetchStatus()
      await fetchList()
    } catch (err) {
      console.error(err)
      toast.error(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleDeregister() {
    if (!jwt) return
    setActionLoading(true)
    try {
      await deregisterEvaluator(jwt)
      toast.info('Successfully deregistered')
      await fetchStatus()
      await fetchList()
    } catch (err) {
      console.error(err)
      toast.error(err instanceof Error ? err.message : 'Deregistration failed')
    } finally {
      setActionLoading(false)
    }
  }

  const filteredArbitrators = arbitrators.filter(a => a.address.toLowerCase().includes(search.toLowerCase()))
  const activeCount = arbitrators.filter(a => a.status === 'active').length
  const totalResolved = arbitrators.reduce((acc, a) => acc + a.disputes_voted, 0)

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.5rem' }}>
          Mediator Directory &amp; Portal
        </h1>
        <p style={{ fontSize: '1.125rem', color: '#94a3b8' }}>
          Independent community arbitrators resolving disputed bounties.
        </p>
      </header>

      {/* User Mediator Status Card */}
      <section style={{
        background: 'rgba(30, 41, 59, 0.4)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '1rem',
        padding: '2rem',
        marginBottom: '3rem',
        backdropFilter: 'blur(12px)',
      }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1.5rem' }}>Your Mediator Status</h2>
        
        {!connected ? (
          <p style={{ color: '#94a3b8' }}>Connect your wallet to view your status and register.</p>
        ) : loadingStatus ? (
          <p style={{ color: '#94a3b8' }}>Loading status...</p>
        ) : status ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '250px' }}>
                <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '0.25rem' }}>Wallet Address</p>
                <p style={{ fontFamily: 'monospace', color: '#e2e8f0', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '0.5rem' }}>
                  {address}
                </p>
              </div>
              <div>
                <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '0.25rem' }}>Current Karma</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#818cf8' }}>{status.karma}</span>
                  {status.karma < status.min_karma_required && (
                    <span style={{ fontSize: '0.75rem', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', padding: '0.125rem 0.5rem', borderRadius: '9999px' }}>
                      Requires &ge; {status.min_karma_required}
                    </span>
                  )}
                </div>
              </div>
              <div>
                <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '0.25rem' }}>Status</p>
                {status.is_registered ? (
                  <span style={{ display: 'inline-block', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.875rem', fontWeight: 600 }}>
                    Active Mediator
                  </span>
                ) : (
                  <span style={{ display: 'inline-block', background: 'rgba(100, 116, 139, 0.1)', color: '#94a3b8', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.875rem', fontWeight: 600 }}>
                    Not Registered
                  </span>
                )}
              </div>
            </div>

            <div style={{ marginTop: '1rem' }}>
              {status.is_registered ? (
                <button
                  onClick={handleDeregister}
                  disabled={actionLoading}
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    color: '#ef4444',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '0.5rem',
                    fontWeight: 600,
                    cursor: actionLoading ? 'not-allowed' : 'pointer',
                    opacity: actionLoading ? 0.7 : 1,
                    transition: 'all 0.2s'
                  }}
                >
                  {actionLoading ? 'Processing...' : 'Deregister'}
                </button>
              ) : status.can_register ? (
                <button
                  onClick={handleRegister}
                  disabled={actionLoading}
                  style={{
                    background: '#6366f1',
                    color: '#ffffff',
                    border: 'none',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '0.5rem',
                    fontWeight: 600,
                    cursor: actionLoading ? 'not-allowed' : 'pointer',
                    opacity: actionLoading ? 0.7 : 1,
                    transition: 'all 0.2s',
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
                  }}
                >
                  {actionLoading ? 'Processing...' : 'Register as Mediator'}
                </button>
              ) : (
                <button
                  disabled
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: '#64748b',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '0.5rem',
                    fontWeight: 600,
                    cursor: 'not-allowed'
                  }}
                >
                  Requires {status.min_karma_required} Karma (Current: {status.karma})
                </button>
              )}
            </div>
          </div>
        ) : null}
      </section>

      {/* Active Mediators List */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#f1f5f9' }}>Community Mediators</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              {activeCount} active &bull; {totalResolved} disputes resolved
            </p>
          </div>
          <input
            type="text"
            placeholder="Search by address..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              background: 'rgba(0,0,0,0.2)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '0.5rem',
              padding: '0.75rem 1rem',
              color: '#f8fafc',
              minWidth: '250px'
            }}
          />
        </div>

        {loadingList ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>Loading mediators...</div>
        ) : filteredArbitrators.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 2rem', background: 'rgba(255,255,255,0.02)', borderRadius: '1rem', border: '1px dashed rgba(255,255,255,0.1)' }}>
            <p style={{ color: '#94a3b8' }}>{search ? 'No mediators found matching search.' : 'No mediators registered yet.'}</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
            {filteredArbitrators.map(arb => (
              <div key={arb.address} style={{
                background: 'rgba(30, 41, 59, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                borderRadius: '0.75rem',
                padding: '1.5rem',
                transition: 'transform 0.2s, border-color 0.2s',
                cursor: 'default'
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)'}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontFamily: 'monospace', color: '#e2e8f0', fontSize: '1.125rem' }}>
                      {arb.address.slice(0, 6)}&hellip;{arb.address.slice(-4)}
                    </span>
                    <button
                      onClick={() => { navigator.clipboard.writeText(arb.address); toast.success('Address copied!') }}
                      title="Copy Address"
                      style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '0.25rem' }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                      </svg>
                    </button>
                  </div>
                  {arb.status === 'active' ? (
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '0.2rem 0.5rem', borderRadius: '0.25rem' }}>Active</span>
                  ) : (
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', background: 'rgba(148, 163, 184, 0.1)', padding: '0.2rem 0.5rem', borderRadius: '0.25rem' }}>Inactive</span>
                  )}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>Karma</p>
                    <p style={{ color: '#818cf8', fontWeight: 700 }}>{arb.karma}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>Registered</p>
                    <p style={{ color: '#cbd5e1', fontSize: '0.875rem' }}>
                      {new Date(arb.registered_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>Assigned</p>
                    <p style={{ color: '#cbd5e1', fontSize: '0.875rem' }}>{arb.disputes_assigned}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>Resolved</p>
                    <p style={{ color: '#cbd5e1', fontSize: '0.875rem' }}>{arb.disputes_voted}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
