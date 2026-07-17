'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/providers'
import { useEvents } from '@/hooks/useEvents'
import type { Bounty, EscrowState, SseEvent, TxnGenWithBreakdown } from '@/types'
import {
  getBounty,
  getClaimTxn,
  claimBounty,
  submitWork,
  getApproveTxn,
  approveWork,
  rejectWork,
  disputeWork,
  getEscrow,
} from '@/lib/api'
import { StatusBadge, Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { FullPageSpinner } from '@/components/ui/Spinner'
import { AlgoBountyError } from '@/types'

function formatAlgo(micro: number) {
  const a = micro / 1_000_000
  return `${a % 1 === 0 ? a.toFixed(0) : a.toFixed(4)} ALGO`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

export default function BountyDetailPage() {
  const params = useParams()
  const router = useRouter()
  const bountyId = params.bounty_id as string

  const { connected, address, jwt, signTransaction } = useAuth()
  const toast = useToast()

  const [bounty, setBounty] = useState<Bounty | null>(null)
  const [escrow, setEscrow] = useState<EscrowState | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [prUrl, setPrUrl] = useState('')
  const [disputeReason, setDisputeReason] = useState('')
  const [showDisputeForm, setShowDisputeForm] = useState(false)
  const [showApprovalModal, setShowApprovalModal] = useState(false)
  const [approvalTxn, setApprovalTxn] = useState<TxnGenWithBreakdown | null>(null)
  const [showClaimModal, setShowClaimModal] = useState(false)
  const [claimTxn, setClaimTxn] = useState<TxnGenWithBreakdown | null>(null)

  const fetchBounty = useCallback(async () => {
    try {
      const b = await getBounty(bountyId)
      setBounty(b)
      if (b.app_id) {
        getEscrow(b.app_id)
          .then(setEscrow)
          .catch(() => null) // escrow may not be indexed yet
      }
    } catch (err) {
      if (err instanceof AlgoBountyError && err.code === 'BountyNotFound') {
        router.push('/')
      }
    } finally {
      setLoading(false)
    }
  }, [bountyId, router])

  useEffect(() => {
    void fetchBounty()
  }, [fetchBounty])

  // Real-time: reload when this bounty changes
  const handleSseEvent = useCallback(
    (event: SseEvent) => {
      if (event.data.bounty_id === bountyId) {
        void fetchBounty()
      }
    },
    [bountyId, fetchBounty],
  )
  useEvents({ onEvent: handleSseEvent })

  if (loading) return <FullPageSpinner />
  if (!bounty) return null

  const isCreator = address === bounty.creator
  const isWorker = address === bounty.worker
  const canClaim = bounty.status === 'open' && connected && !isCreator
  const canSubmit = bounty.status === 'claimed' && isWorker
  const canApprove = bounty.status === 'submitted' && isCreator
  const canReject = bounty.status === 'submitted' && isCreator
  const canDispute = (bounty.status === 'submitted' || bounty.status === 'claimed') && (isCreator || isWorker)

  const handleClaim = async () => {
    if (!jwt) return
    setActionLoading(true)
    try {
      const data = await getClaimTxn(bountyId, jwt)
      setClaimTxn(data)
      setShowClaimModal(true)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to prepare claim')
    } finally {
      setActionLoading(false)
    }
  }

  const handleConfirmClaim = async () => {
    if (!claimTxn || !jwt) return
    try {
      setActionLoading(true)
      const signedTxn = await signTransaction(claimTxn.unsigned_txn)
      await claimBounty(bountyId, signedTxn, jwt)
      toast.success('Bounty claimed! You are now the worker.')
      setShowClaimModal(false)
      setClaimTxn(null)
      void fetchBounty()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to claim bounty')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancelClaim = () => {
    setShowClaimModal(false)
    setClaimTxn(null)
  }

  const handleSubmit = async () => {
    if (!jwt || !prUrl.trim()) return
    setActionLoading(true)
    try {
      await submitWork(bountyId, { pr_url: prUrl.trim() }, jwt)
      toast.success('Work submitted for review!')
      void fetchBounty()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to submit work')
    } finally {
      setActionLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!jwt) return
    setActionLoading(true)
    try {
      const data = await getApproveTxn(bountyId, jwt)
      setApprovalTxn(data)
      setShowApprovalModal(true)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to prepare approval')
    } finally {
      setActionLoading(false)
    }
  }

  const handleConfirmApprove = async () => {
    if (!approvalTxn || !jwt) return
    try {
      setActionLoading(true)
      const signedTxn = await signTransaction(approvalTxn.unsigned_txn)
      await approveWork(bountyId, signedTxn, jwt)
      toast.success('Work approved! Funds released to worker. ✅')
      setShowApprovalModal(false)
      setApprovalTxn(null)
      void fetchBounty()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to approve work')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancelApprove = () => {
    setShowApprovalModal(false)
    setApprovalTxn(null)
  }

  const handleReject = async () => {
    if (!jwt) return
    setActionLoading(true)
    try {
      await rejectWork(bountyId, jwt)
      toast.warning('Work rejected. Worker may resubmit.')
      void fetchBounty()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to reject work')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDispute = async () => {
    if (!jwt) return
    setActionLoading(true)
    try {
      await disputeWork(bountyId, jwt, disputeReason || undefined)
      toast.info('Dispute raised. A mediator will review.')
      setShowDisputeForm(false)
      void fetchBounty()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to raise dispute')
    } finally {
      setActionLoading(false)
    }
  }

  const sectionStyle: React.CSSProperties = {
    background: 'rgba(10,10,22,0.7)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '1rem',
    padding: '1.5rem',
  }

  return (
    <div
      className="fade-in"
      style={{
        maxWidth: '900px',
        margin: '0 auto',
        padding: 'clamp(1.5rem, 4vw, 2.5rem) clamp(1rem, 4vw, 2rem)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}
    >
      {/* Breadcrumb */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: '#475569' }}>
        <Link href="/" style={{ color: '#6366f1' }}>Marketplace</Link>
        <span>/</span>
        <span style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}>{bountyId}</span>
      </nav>

      {/* Header card */}
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <StatusBadge status={bounty.status} />
            {bounty.treasury_altered && <Badge variant="altered">CUSTOM PAYOUT</Badge>}
          </div>
          <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#475569', padding: '0.25rem 0.5rem', background: 'rgba(255,255,255,0.04)', borderRadius: '0.375rem' }}>
            {bounty.bounty_id}
          </span>
        </div>
        <h1
          style={{
            margin: '0 0 1.5rem',
            fontSize: 'clamp(1.25rem, 3vw, 1.75rem)',
            fontWeight: 800,
            color: '#f1f5f9',
            lineHeight: 1.35,
          }}
        >
          {bounty.description}
        </h1>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '1rem',
          }}
        >
          {[
            { label: 'Reward', value: <span style={{ color: '#22d3ee', fontWeight: 800, fontSize: '1.25rem' }}>{formatAlgo(bounty.amount)}</span> },
            { label: 'Status', value: <StatusBadge status={bounty.status} /> },
            { label: 'HITM', value: bounty.hitm ? <Badge variant="hitm">Enabled</Badge> : <span style={{ color: '#475569' }}>Disabled</span> },
            { label: 'Karma Required', value: <span style={{ color: '#818cf8' }}>★ {bounty.karma_required}</span> },
            { label: 'Created', value: <span style={{ color: '#64748b', fontSize: '0.875rem' }}>{formatDate(bounty.created_at)}</span> },
            bounty.deadline_rounds_remaining != null && { label: 'Rounds Left', value: <span style={{ color: '#f59e0b' }}>{bounty.deadline_rounds_remaining.toLocaleString()}</span> },
          ].filter(Boolean).map((item) => item && (
            <div key={item.label}>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.375rem' }}>{item.label}</div>
              <div>{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Creator / Worker */}
      <div style={{ ...sectionStyle, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div>
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.5rem' }}>Creator</div>
          <Link href={`/agents/${bounty.creator}`} style={{ fontFamily: 'monospace', fontSize: '0.875rem', color: '#6366f1' }}>
            {bounty.creator?.slice(0, 12)}…{bounty.creator?.slice(-6)}
          </Link>
        </div>
        {bounty.worker && (
          <div>
            <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.5rem' }}>Worker</div>
            <Link href={`/agents/${bounty.worker}`} style={{ fontFamily: 'monospace', fontSize: '0.875rem', color: '#10b981' }}>
              {bounty.worker?.slice(0, 12)}…{bounty.worker?.slice(-6)}
            </Link>
          </div>
        )}
      </div>

      {/* Repo + Tags */}
      {(bounty.repo_url || (bounty.tags && bounty.tags.length > 0) || (bounty.repo_labels && bounty.repo_labels.length > 0)) && (
        <div style={sectionStyle}>
          {bounty.repo_url && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.5rem' }}>Repository</div>
              <a href={bounty.repo_url} target="_blank" rel="noopener noreferrer" style={{ color: '#6366f1', fontSize: '0.9375rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
                {bounty.repo_url.replace('https://', '')}
              </a>
            </div>
          )}
          {bounty.repo_labels && bounty.repo_labels.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.5rem' }}>Labels</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                {bounty.repo_labels.map((l) => <Badge key={l}>{l}</Badge>)}
              </div>
            </div>
          )}
          {bounty.tags && bounty.tags.length > 0 && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.5rem' }}>Tags</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                {bounty.tags.map((t) => <Badge key={t} variant="default">{t}</Badge>)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Escrow panel */}
      {bounty.app_id && (
        <div style={sectionStyle}>
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', fontWeight: 600, marginBottom: '0.75rem' }}>Escrow Contract</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#475569', marginBottom: '0.25rem' }}>App ID</div>
              <span style={{ fontFamily: 'monospace', color: '#818cf8', fontWeight: 600 }}>#{bounty.app_id}</span>
            </div>
            {escrow && (
              <>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#475569', marginBottom: '0.25rem' }}>On-chain State</div>
                  <span style={{ fontFamily: 'monospace', color: '#22d3ee', fontSize: '0.875rem' }}>{escrow.state}</span>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#475569', marginBottom: '0.25rem' }}>Balance</div>
                  <span style={{ color: '#22d3ee', fontWeight: 700 }}>{formatAlgo(escrow.balance)}</span>
                </div>
                {escrow.payout_type && (
                  <div>
                    <div style={{ fontSize: '0.75rem', color: '#475569', marginBottom: '0.25rem' }}>Payout Type</div>
                    <Badge>{escrow.payout_type}</Badge>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Action panel */}
      {connected && (
        <div style={{ ...sectionStyle, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>Actions</h3>

          {/* Claim */}
          {canClaim && (
            <Button id="claim-btn" fullWidth loading={actionLoading} onClick={() => void handleClaim()}>
              🤝 Claim This Bounty
            </Button>
          )}

          {/* Submit work */}
          {canSubmit && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <input
                id="pr-url-input"
                type="url"
                placeholder="https://github.com/org/repo/pull/42"
                value={prUrl}
                onChange={(e) => setPrUrl(e.target.value)}
                style={{
                  padding: '0.625rem 0.875rem',
                  borderRadius: '0.625rem',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#e2e8f0',
                  fontSize: '0.9375rem',
                  fontFamily: 'monospace',
                  outline: 'none',
                  width: '100%',
                }}
              />
              <Button
                id="submit-work-btn"
                fullWidth
                loading={actionLoading}
                disabled={!prUrl.trim()}
                onClick={() => void handleSubmit()}
              >
                📬 Submit Work
              </Button>
            </div>
          )}

          {/* Creator actions */}
          {(canApprove || canReject) && (
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Button
                id="approve-btn"
                loading={actionLoading}
                onClick={() => void handleApprove()}
                style={{ flex: 1, minWidth: '140px' }}
              >
                ✅ Approve & Release
              </Button>
              <Button
                id="reject-btn"
                variant="warning"
                loading={actionLoading}
                onClick={() => void handleReject()}
                style={{ flex: 1, minWidth: '140px' }}
              >
                ↩ Request Revision
              </Button>
            </div>
          )}

          {/* Dispute */}
          {canDispute && !showDisputeForm && (
            <Button
              id="dispute-btn"
              variant="danger"
              size="sm"
              onClick={() => setShowDisputeForm(true)}
            >
              ⚖️ Raise Dispute
            </Button>
          )}
          {showDisputeForm && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <textarea
                id="dispute-reason"
                placeholder="Describe the reason for this dispute…"
                value={disputeReason}
                onChange={(e) => setDisputeReason(e.target.value)}
                rows={3}
                style={{
                  padding: '0.625rem 0.875rem',
                  borderRadius: '0.625rem',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  color: '#e2e8f0',
                  fontSize: '0.9375rem',
                  resize: 'vertical',
                  fontFamily: 'inherit',
                  outline: 'none',
                  width: '100%',
                }}
              />
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <Button id="confirm-dispute-btn" variant="danger" loading={actionLoading} onClick={() => void handleDispute()}>Confirm Dispute</Button>
                <Button variant="ghost" onClick={() => setShowDisputeForm(false)}>Cancel</Button>
              </div>
            </div>
          )}

          {bounty.status === 'disputed' && (
            <div style={{ padding: '1rem', borderRadius: '0.75rem', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#fca5a5', fontSize: '0.9375rem' }}>
              ⚖️ This bounty is under dispute. A mediator will resolve it within 30 days.
            </div>
          )}

          {(bounty.status === 'approved' || bounty.status === 'closed') && (
            <div style={{ padding: '1rem', borderRadius: '0.75rem', background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', color: '#6ee7b7', fontSize: '0.9375rem', textAlign: 'center' }}>
              ✅ Completed — funds have been released
            </div>
          )}

          {bounty.status === 'refunded' && (
            <div style={{ padding: '1rem', borderRadius: '0.75rem', background: 'rgba(148,163,184,0.08)', border: '1px solid rgba(148,163,184,0.15)', color: '#94a3b8', fontSize: '0.9375rem', textAlign: 'center' }}>
              Bounty was refunded to creator
            </div>
          )}
        </div>
      )}

      {/* Approval Confirmation Modal (FR-001, FR-002, FR-005) */}
      {showApprovalModal && approvalTxn && bounty && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.7)', padding: '1rem' }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '1rem', maxWidth: '480px', width: '100%', padding: '1.5rem', color: '#e2e8f0' }}>
            <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1.25rem', fontWeight: 600 }}>✅ Approve &amp; Release</h3>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', margin: '0 0 1rem 0' }}>
              Review the fee breakdown before signing. This action will release escrowed funds.
            </p>

            {/* Fee breakdown table */}
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9375rem', marginBottom: '1.25rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                  <th style={{ padding: '0.5rem 0.75rem 0.5rem 0', color: '#94a3b8', fontWeight: 500 }}>Item</th>
                  <th style={{ padding: '0.5rem 0 0.5rem 0.75rem', color: '#94a3b8', fontWeight: 500, textAlign: 'right' }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0' }}>Total Released</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>{approvalTxn.fee_breakdown_display.total}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#6ee7b7' }}>Developer Royalty (1%)</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#6ee7b7' }}>{approvalTxn.fee_breakdown_display.developer_royalty}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#94a3b8' }}>Platform Treasury (1%)</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#94a3b8' }}>{approvalTxn.fee_breakdown_display.platform_treasury}</td>
                </tr>
                {bounty.hitm && approvalTxn.fee_breakdown.mediator_fee > 0 && (
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#94a3b8' }}>Mediator Fee (0.25%)</td>
                    <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#94a3b8' }}>{approvalTxn.fee_breakdown_display.mediator_fee}</td>
                  </tr>
                )}
                {bounty.hitm && approvalTxn.fee_breakdown.mediator_fee === 0 && (
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#64748b' }}>Mediator Fee (0.25%)</td>
                    <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#64748b' }}>0 ALGO</td>
                  </tr>
                )}
                {!bounty.hitm && (
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#64748b' }}>Mediator Fee (0.25%)</td>
                    <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#64748b' }}><i>Not applicable</i></td>
                  </tr>
                )}
                <tr>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', fontWeight: 600 }}>Claimant Payout</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', fontWeight: 700, fontSize: '1.0625rem' }}>{approvalTxn.fee_breakdown_display.claimant_payout}</td>
                </tr>
              </tbody>
            </table>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Button variant="secondary" style={{ flex: 1 }} onClick={handleCancelApprove}>
                Cancel
              </Button>
              <Button
                id="confirm-approve-btn"
                style={{ flex: 1 }}
                onClick={handleConfirmApprove}
                loading={actionLoading}
              >
                Confirm &amp; Sign
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Claim Confirmation Modal (FR-002, FR-005) */}
      {showClaimModal && claimTxn && bounty && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.7)', padding: '1rem' }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '1rem', maxWidth: '480px', width: '100%', padding: '1.5rem', color: '#e2e8f0' }}>
            <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1.25rem', fontWeight: 600 }}>🤝 Claim Bounty</h3>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', margin: '0 0 1rem 0' }}>
              Review the fee breakdown before signing. You will be committing escrow funds to the contract.
            </p>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9375rem', marginBottom: '1.25rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                  <th style={{ padding: '0.5rem 0.75rem 0.5rem 0', color: '#94a3b8', fontWeight: 500 }}>Item</th>
                  <th style={{ padding: '0.5rem 0 0.5rem 0.75rem', color: '#94a3b8', fontWeight: 500, textAlign: 'right' }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0' }}>Total Escrow</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>{claimTxn.fee_breakdown_display.total}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#6ee7b7' }}>Developer Royalty (1%)</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#6ee7b7' }}>{claimTxn.fee_breakdown_display.developer_royalty}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#94a3b8' }}>Platform Treasury (1%)</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#94a3b8' }}>{claimTxn.fee_breakdown_display.platform_treasury}</td>
                </tr>
                {bounty.hitm && claimTxn.fee_breakdown.mediator_fee > 0 && (
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#94a3b8' }}>Mediator Fee (0.25%)</td>
                    <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#94a3b8' }}>{claimTxn.fee_breakdown_display.mediator_fee}</td>
                  </tr>
                )}
                {bounty.hitm && claimTxn.fee_breakdown.mediator_fee === 0 && (
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#64748b' }}>Mediator Fee (0.25%)</td>
                    <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#64748b' }}>0 ALGO</td>
                  </tr>
                )}
                {!bounty.hitm && (
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', color: '#64748b' }}>Mediator Fee (0.25%)</td>
                    <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', color: '#64748b' }}><i>Not applicable</i></td>
                  </tr>
                )}
                <tr>
                  <td style={{ padding: '0.625rem 0.75rem 0.625rem 0', fontWeight: 600 }}>Worker Payout</td>
                  <td style={{ padding: '0.625rem 0 0.625rem 0.75rem', textAlign: 'right', fontWeight: 700, fontSize: '1.0625rem' }}>{claimTxn.fee_breakdown_display.claimant_payout}</td>
                </tr>
              </tbody>
            </table>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Button variant="secondary" style={{ flex: 1 }} onClick={handleCancelClaim}>
                Cancel
              </Button>
              <Button
                id="confirm-claim-btn"
                style={{ flex: 1 }}
                onClick={handleConfirmClaim}
                loading={actionLoading}
              >
                Confirm &amp; Sign
              </Button>
            </div>
          </div>
        </div>
      )}

      {!connected && (
        <div
          style={{
            textAlign: 'center',
            padding: '2rem',
            background: 'rgba(99,102,241,0.06)',
            border: '1px solid rgba(99,102,241,0.15)',
            borderRadius: '1rem',
            color: '#818cf8',
            fontSize: '0.9375rem',
          }}
        >
          Connect your wallet to interact with this bounty
        </div>
      )}
    </div>
  )
}