'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/providers'
import { createBounty } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'

// ─── Constants ────────────────────────────────────────────────────────────────

const ASSET_OPTIONS = [
  { id: 0, name: 'ALGO' },
  { id: 10458941, name: 'USDC (Testnet)' },
]

const DEFAULT_DEADLINE_ROUNDS = 100_000 // ~5 days on Algorand

// ─── Form state ───────────────────────────────────────────────────────────────

interface FormState {
  description: string
  amountAlgo: string
  assetId: number
  hitm: boolean
  deadlineRounds: string
  repoUrl: string
  repoLabels: string
  karmaRequired: string
  tags: string
  githubIssue: string
  hitmReviewDays: string
}

const INITIAL: FormState = {
  description: '',
  amountAlgo: '',
  assetId: 0,
  hitm: false,
  deadlineRounds: String(DEFAULT_DEADLINE_ROUNDS),
  repoUrl: '',
  repoLabels: '',
  karmaRequired: '0',
  tags: '',
  githubIssue: '',
  hitmReviewDays: '3',
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const fieldStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.375rem',
}

const labelStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.07em',
  color: '#64748b',
}

const inputStyle: React.CSSProperties = {
  padding: '0.625rem 0.875rem',
  borderRadius: '0.625rem',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.1)',
  color: '#e2e8f0',
  fontSize: '0.9375rem',
  outline: 'none',
  width: '100%',
  transition: 'border-color 0.15s',
}

const sectionStyle: React.CSSProperties = {
  background: 'rgba(10,10,22,0.7)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: '1rem',
  padding: '1.5rem',
  display: 'flex',
  flexDirection: 'column',
  gap: '1.25rem',
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function CreateBountyPage() {
  const router = useRouter()
  const { connected, jwt, karma } = useAuth()
  const toast = useToast()

  const [form, setForm] = useState<FormState>(INITIAL)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})

  const set = (field: keyof FormState, value: string | boolean | number) =>
    setForm((prev) => ({ ...prev, [field]: value }))

  // ─── Validation ──────────────────────────────────────────────────────────

  const validate = (): boolean => {
    const errs: Partial<Record<keyof FormState, string>> = {}
    if (!form.description.trim()) errs.description = 'Description is required'
    if (!form.amountAlgo || Number(form.amountAlgo) <= 0) errs.amountAlgo = 'Must be > 0'
    if (!form.repoUrl.trim()) errs.repoUrl = 'Repository URL is required'
    const rounds = Number(form.deadlineRounds)
    if (!rounds || rounds < 100) errs.deadlineRounds = 'Minimum 100 rounds'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  // ─── Submit ──────────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!jwt) {
      toast.error('Please connect your wallet first')
      return
    }
    if (!validate()) return

    setLoading(true)
    try {
      const payload = {
        description: form.description.trim(),
        amount: Math.round(Number(form.amountAlgo) * 1_000_000),
        asset_id: form.assetId,
        hitm: form.hitm,
        deadline_rounds: Number(form.deadlineRounds),
        repo_url: form.repoUrl.trim(),
        repo_labels: form.repoLabels
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        karma_requirement: Number(form.karmaRequired) || 0,
        tags: form.tags
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        ...(form.githubIssue ? { github_issue: Number(form.githubIssue) } : {}),
        ...(form.hitm && form.hitmReviewDays
          ? { hitm_review_days: Number(form.hitmReviewDays) }
          : {}),
      }

      const result = await createBounty(payload, jwt)
      toast.success(`Bounty created! ID: ${result.bounty_id}`)
      router.push(`/bounties/${result.bounty_id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create bounty')
    } finally {
      setLoading(false)
    }
  }

  // ─── Not connected ───────────────────────────────────────────────────────

  if (!connected) {
    return (
      <div
        className="fade-in"
        style={{
          maxWidth: '600px',
          margin: '4rem auto',
          padding: '0 1.5rem',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            padding: '3rem',
            background: 'rgba(99,102,241,0.06)',
            border: '1px solid rgba(99,102,241,0.15)',
            borderRadius: '1.25rem',
          }}
        >
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔐</div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9', marginBottom: '0.75rem' }}>
            Connect Your Wallet
          </h1>
          <p style={{ color: '#64748b', marginBottom: '1.5rem' }}>
            You need a connected wallet to create a bounty.
          </p>
          <Link href="/">
            <Button>← Back to Marketplace</Button>
          </Link>
        </div>
      </div>
    )
  }

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div
      className="fade-in"
      style={{
        maxWidth: '720px',
        margin: '0 auto',
        padding: 'clamp(1.5rem, 4vw, 2.5rem) clamp(1rem, 4vw, 1.5rem)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}
    >
      {/* Header */}
      <div>
        <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: '#475569', marginBottom: '1.25rem' }}>
          <Link href="/" style={{ color: '#6366f1' }}>Marketplace</Link>
          <span>/</span>
          <span>Create Bounty</span>
        </nav>
        <h1 style={{ margin: 0, fontSize: 'clamp(1.5rem, 4vw, 2rem)', fontWeight: 900, color: '#f1f5f9' }}>
          Create Bounty
        </h1>
        <p style={{ margin: '0.5rem 0 0', color: '#64748b' }}>
          Post a task and escrow the reward on Algorand.{' '}
          <span style={{ color: '#818cf8' }}>★ Your karma: {karma}</span>
        </p>
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Bounty Details */}
        <div style={sectionStyle}>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>Bounty Details</h2>

          <div style={fieldStyle}>
            <label htmlFor="description" style={labelStyle}>Description *</label>
            <textarea
              id="description"
              rows={4}
              placeholder="Describe the task clearly — what needs to be built, fixed, or researched…"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.6 }}
            />
            {errors.description && <span style={{ color: '#ef4444', fontSize: '0.8rem' }}>{errors.description}</span>}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={fieldStyle}>
              <label htmlFor="amount" style={labelStyle}>Reward Amount *</label>
              <div style={{ position: 'relative' }}>
                <input
                  id="amount"
                  type="number"
                  min="0.001"
                  step="0.001"
                  placeholder="e.g. 100"
                  value={form.amountAlgo}
                  onChange={(e) => set('amountAlgo', e.target.value)}
                  style={{ ...inputStyle, paddingRight: '4rem' }}
                />
                <span style={{ position: 'absolute', right: '0.875rem', top: '50%', transform: 'translateY(-50%)', color: '#475569', fontSize: '0.875rem', pointerEvents: 'none' }}>
                  ALGO
                </span>
              </div>
              {errors.amountAlgo && <span style={{ color: '#ef4444', fontSize: '0.8rem' }}>{errors.amountAlgo}</span>}
            </div>

            <div style={fieldStyle}>
              <label htmlFor="asset" style={labelStyle}>Asset</label>
              <select
                id="asset"
                value={form.assetId}
                onChange={(e) => set('assetId', Number(e.target.value))}
                style={{ ...inputStyle, cursor: 'pointer' }}
              >
                {ASSET_OPTIONS.map((a) => (
                  <option key={a.id} value={a.id} style={{ background: '#0f0f1a' }}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={fieldStyle}>
              <label htmlFor="deadline" style={labelStyle}>Deadline (rounds)</label>
              <input
                id="deadline"
                type="number"
                min="100"
                step="100"
                value={form.deadlineRounds}
                onChange={(e) => set('deadlineRounds', e.target.value)}
                style={inputStyle}
              />
              {errors.deadlineRounds && <span style={{ color: '#ef4444', fontSize: '0.8rem' }}>{errors.deadlineRounds}</span>}
              <span style={{ fontSize: '0.75rem', color: '#475569' }}>
                ~{Math.round(Number(form.deadlineRounds || 0) / 20_000 * 100) / 100} days
              </span>
            </div>

            <div style={fieldStyle}>
              <label htmlFor="karma" style={labelStyle}>Min Karma Required</label>
              <input
                id="karma"
                type="number"
                min="0"
                step="1"
                value={form.karmaRequired}
                onChange={(e) => set('karmaRequired', e.target.value)}
                style={inputStyle}
              />
            </div>
          </div>
        </div>

        {/* Repository */}
        <div style={sectionStyle}>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>Repository</h2>

          <div style={fieldStyle}>
            <label htmlFor="repo-url" style={labelStyle}>GitHub Repository URL *</label>
            <input
              id="repo-url"
              type="url"
              placeholder="https://github.com/org/repo"
              value={form.repoUrl}
              onChange={(e) => set('repoUrl', e.target.value)}
              style={inputStyle}
            />
            {errors.repoUrl && <span style={{ color: '#ef4444', fontSize: '0.8rem' }}>{errors.repoUrl}</span>}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={fieldStyle}>
              <label htmlFor="repo-labels" style={labelStyle}>Labels (comma-separated)</label>
              <input
                id="repo-labels"
                type="text"
                placeholder="bug, enhancement"
                value={form.repoLabels}
                onChange={(e) => set('repoLabels', e.target.value)}
                style={inputStyle}
              />
            </div>

            <div style={fieldStyle}>
              <label htmlFor="github-issue" style={labelStyle}>GitHub Issue # (optional)</label>
              <input
                id="github-issue"
                type="number"
                min="1"
                placeholder="42"
                value={form.githubIssue}
                onChange={(e) => set('githubIssue', e.target.value)}
                style={inputStyle}
              />
            </div>
          </div>

          <div style={fieldStyle}>
            <label htmlFor="tags" style={labelStyle}>Tags (comma-separated)</label>
            <input
              id="tags"
              type="text"
              placeholder="solidity, defi, frontend"
              value={form.tags}
              onChange={(e) => set('tags', e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>

        {/* HITM */}
        <div style={sectionStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
            <div>
              <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
                Human-in-the-Middle (HITM) Mode
              </h2>
              <p style={{ margin: 0, fontSize: '0.875rem', color: '#475569' }}>
                Require manual creator review before payout. Adds a review deadline.
              </p>
            </div>
            <button
              type="button"
              id="hitm-toggle"
              role="switch"
              aria-checked={form.hitm}
              onClick={() => set('hitm', !form.hitm)}
              style={{
                width: '3rem',
                height: '1.625rem',
                borderRadius: '999px',
                background: form.hitm ? '#6366f1' : 'rgba(255,255,255,0.1)',
                border: 'none',
                cursor: 'pointer',
                position: 'relative',
                flexShrink: 0,
                transition: 'background 0.2s',
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  top: '3px',
                  left: form.hitm ? 'calc(100% - 22px)' : '3px',
                  width: '19px',
                  height: '19px',
                  borderRadius: '50%',
                  background: '#fff',
                  transition: 'left 0.2s',
                }}
              />
            </button>
          </div>

          {form.hitm && (
            <div style={fieldStyle}>
              <label htmlFor="hitm-days" style={labelStyle}>Review Window (days)</label>
              <input
                id="hitm-days"
                type="number"
                min="1"
                max="30"
                value={form.hitmReviewDays}
                onChange={(e) => set('hitmReviewDays', e.target.value)}
                style={{ ...inputStyle, maxWidth: '160px' }}
              />
            </div>
          )}
        </div>

        {/* Preview */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderRadius: '0.75rem',
            background: 'rgba(99,102,241,0.06)',
            border: '1px solid rgba(99,102,241,0.15)',
            fontSize: '0.875rem',
            color: '#818cf8',
          }}
        >
          <strong>Escrow amount:</strong>{' '}
          {form.amountAlgo ? `${form.amountAlgo} ALGO` : '—'}{' '}
          <span style={{ color: '#475569' }}>
            + ~0.002 ALGO network fees · Locked on-chain until completion
          </span>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <Link href="/">
            <Button type="button" variant="ghost">Cancel</Button>
          </Link>
          <Button id="create-bounty-btn" type="submit" loading={loading}>
            🚀 Create &amp; Escrow
          </Button>
        </div>
      </form>
    </div>
  )
}
