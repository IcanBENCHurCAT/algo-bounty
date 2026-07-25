'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { getBounties, adminResolveDispute, getQuarantines, resolveQuarantine, Bounty } from '@/lib/api'

interface QuarantineRecord {
  id: number
  address: string
  bounty_id?: string
  reason: string
  details?: string
  quarantined_at: string
  expires_at: string
  status: string
  resolved_by?: string
  resolved_at?: string
  resolution_note?: string
}

export default function AdminPortalPage() {
  const { jwt, address } = useAuth()
  const [activeTab, setActiveTab] = useState<'disputes' | 'quarantines'>('disputes')
  const [disputedBounties, setDisputedBounties] = useState<Bounty[]>([])
  const [quarantines, setQuarantines] = useState<QuarantineRecord[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [resolutionNote, setResolutionNote] = useState<string>('')

  const fetchData = async () => {
    setLoading(true)
    setMessage(null)
    try {
      // Fetch disputed bounties
      const res = await getBounties({ status: 'disputed' })
      setDisputedBounties((res.bounties || []).filter((b) => b.status === 'disputed'))

      // Fetch quarantines if authenticated
      if (jwt) {
        try {
          const qData = await getQuarantines(jwt)
          setQuarantines(qData.quarantines || [])
        } catch (e: any) {
          console.warn('Failed to fetch quarantines:', e.message)
        }
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to load admin data.' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [jwt])

  const handleResolveDispute = async (bountyId: string, resolution: 'worker_win' | 'creator_win' | 'split') => {
    if (!jwt) {
      setMessage({ type: 'error', text: 'Authentication token required.' })
      return
    }
    setActionLoading(bountyId)
    setMessage(null)
    try {
      await adminResolveDispute(bountyId, resolution, resolutionNote || 'Admin review completed', jwt)
      setMessage({ type: 'success', text: `Dispute for bounty ${bountyId} resolved (${resolution}).` })
      setResolutionNote('')
      await fetchData()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to resolve dispute.' })
    } finally {
      setActionLoading(null)
    }
  }

  const handleResolveQuarantine = async (qId: number, action: 'clear' | 'penalize') => {
    if (!jwt) {
      setMessage({ type: 'error', text: 'Authentication token required.' })
      return
    }
    setActionLoading(`q-${qId}`)
    setMessage(null)
    try {
      await resolveQuarantine(qId, action, resolutionNote || 'Admin review completed', action === 'penalize' ? 100 : 0, jwt)
      setMessage({ type: 'success', text: `Quarantine #${qId} resolved (${action}).` })
      setResolutionNote('')
      await fetchData()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to resolve quarantine.' })
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-slate-100">Admin Management Portal</h1>
          </div>
          <p className="text-slate-400 text-sm">
            Phase 1 Pre-Mainnet Stewardship — Review open disputes and manage account quarantines.
          </p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/80 rounded-lg transition-colors"
        >
          <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Notification Toast */}
      {message && (
        <div
          className={`p-4 rounded-lg border flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="text-xs opacity-60 hover:opacity-100">
            Dismiss
          </button>
        </div>
      )}

      {/* Resolution Note Input */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Admin Resolution Reason / Note
        </label>
        <input
          type="text"
          value={resolutionNote}
          onChange={(e) => setResolutionNote(e.target.value)}
          placeholder="Optional note explaining resolution decision..."
          className="w-full px-3 py-2 text-sm bg-slate-950/80 border border-slate-700/80 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('disputes')}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'disputes'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Disputed Bounties ({disputedBounties.length})
        </button>

        <button
          onClick={() => setActiveTab('quarantines')}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'quarantines'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Account Quarantines ({quarantines.length})
        </button>
      </div>

      {/* Tab 1: Disputed Bounties */}
      {activeTab === 'disputes' && (
        <div className="space-y-4">
          {loading && disputedBounties.length === 0 ? (
            <div className="p-8 text-center text-slate-500">Loading disputed bounties...</div>
          ) : disputedBounties.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400">
              No active disputed bounties requiring resolution.
            </div>
          ) : (
            disputedBounties.map((b) => (
              <div
                key={b.bounty_id}
                className="p-6 rounded-xl bg-slate-900/80 border border-amber-500/20 space-y-4 shadow-lg"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
                  <div>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 mr-2">
                      DISPUTED
                    </span>
                    <h3 className="text-lg font-bold text-slate-100 inline">{b.description}</h3>
                    <p className="text-xs text-slate-400 mt-1 font-mono">Bounty ID: {b.bounty_id}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xl font-extrabold text-emerald-400">{(b.amount / 1_000_000).toLocaleString()} ALGO</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
                  {b.repo_url && (
                    <div>
                      <span className="text-slate-500">Repository:</span>{' '}
                      <a
                        href={b.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-400 hover:underline inline-flex items-center gap-1"
                      >
                        {b.repo_url}
                      </a>
                    </div>
                  )}
                  <div>
                    <span className="text-slate-500">Creator:</span>{' '}
                    <span className="font-mono text-slate-300">{b.creator}</span>
                  </div>
                  {b.worker && (
                    <div>
                      <span className="text-slate-500">Worker:</span>{' '}
                      <span className="font-mono text-slate-300">{b.worker}</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-wrap gap-3 pt-2 border-t border-slate-800/60">
                  <button
                    onClick={() => handleResolveDispute(b.bounty_id, 'worker_win')}
                    disabled={actionLoading === b.bounty_id}
                    className="px-4 py-2 text-xs font-semibold text-emerald-950 bg-emerald-400 hover:bg-emerald-300 rounded-lg transition-colors shadow"
                  >
                    Worker Win (Payout)
                  </button>

                  <button
                    onClick={() => handleResolveDispute(b.bounty_id, 'creator_win')}
                    disabled={actionLoading === b.bounty_id}
                    className="px-4 py-2 text-xs font-semibold text-rose-950 bg-rose-400 hover:bg-rose-300 rounded-lg transition-colors shadow"
                  >
                    Creator Win (Refund)
                  </button>

                  <button
                    onClick={() => handleResolveDispute(b.bounty_id, 'split')}
                    disabled={actionLoading === b.bounty_id}
                    className="px-4 py-2 text-xs font-semibold text-amber-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors shadow"
                  >
                    50/50 Split
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 2: Account Quarantines */}
      {activeTab === 'quarantines' && (
        <div className="space-y-4">
          {loading && quarantines.length === 0 ? (
            <div className="p-8 text-center text-slate-500">Loading account quarantines...</div>
          ) : quarantines.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400">
              No account quarantines recorded.
            </div>
          ) : (
            quarantines.map((q) => (
              <div
                key={q.id}
                className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 shadow"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded border ${
                        q.status === 'active'
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      }`}
                    >
                      {q.status.toUpperCase()}
                    </span>
                    <span className="font-mono text-sm text-slate-200">{q.address}</span>
                  </div>
                  <span className="text-xs text-slate-500">
                    Quarantined: {new Date(q.quarantined_at).toLocaleString()}
                  </span>
                </div>

                <div className="space-y-1 text-xs text-slate-400">
                  <p>
                    <strong className="text-slate-300">Reason:</strong> {q.reason}
                  </p>
                  {q.details && (
                    <p>
                      <strong className="text-slate-300">Details:</strong> {q.details}
                    </p>
                  )}
                  {q.resolved_by && (
                    <p>
                      <strong className="text-slate-300">Resolved by:</strong> {q.resolved_by} ({q.status})
                    </p>
                  )}
                </div>

                {q.status === 'active' && (
                  <div className="flex gap-3 pt-2 border-t border-slate-800/60">
                    <button
                      onClick={() => handleResolveQuarantine(q.id, 'clear')}
                      disabled={actionLoading === `q-${q.id}`}
                      className="px-4 py-2 text-xs font-semibold text-emerald-950 bg-emerald-400 hover:bg-emerald-300 rounded-lg transition-colors"
                    >
                      Clear Quarantine
                    </button>
                    <button
                      onClick={() => handleResolveQuarantine(q.id, 'penalize')}
                      disabled={actionLoading === `q-${q.id}`}
                      className="px-4 py-2 text-xs font-semibold text-rose-950 bg-rose-400 hover:bg-rose-300 rounded-lg transition-colors"
                    >
                      Penalize (-100 Karma)
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
