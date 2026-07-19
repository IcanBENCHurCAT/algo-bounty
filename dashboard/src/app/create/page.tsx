'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/providers'
import { createBounty } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { useFeeBreakdown } from '@/hooks/useFeeBreakdown'
import { FeeBreakdownTable } from '@/components/ui/FeeBreakdownTable'

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
  platformFee: string
  treasuryAddress: string
  developerFee: string
  taxAccepted: boolean
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
  platformFee: '2.0',
  treasuryAddress: '',
  developerFee: '1.0',
  taxAccepted: false,
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
  color: 'var(--color-text-secondary)',
}

const inputStyle: React.CSSProperties = {
  padding: '0.625rem 0.875rem',
  borderRadius: '0.625rem',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.1)',
  color: 'var(--color-text-primary)',
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
  const [showAdvanced, setShowAdvanced] = useState(false)

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

    const pf = Number(form.platformFee)
    if (isNaN(pf) || pf < 0 || pf > 10) {
      errs.platformFee = 'Platform fee must be between 0% and 10%'
    }

    const df = Number(form.developerFee)
    if (isNaN(df) || df < 0 || df > pf) {
      errs.developerFee = `Developer fee must be between 0% and Platform Fee (${pf}%)`
    }

    if (form.treasuryAddress.trim() && !/^[A-Z2-7]{58}$/.test(form.treasuryAddress.trim())) {
      errs.treasuryAddress = 'Invalid Algorand address format (must be 58 characters, uppercase A-Z, 2-7)'
    }

    if (!form.taxAccepted) {
      errs.taxAccepted = 'You must accept the tax liability disclaimer'
    }

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
        platform_fee: Math.round(Number(form.platformFee) * 100),
        developer_fee: Math.round(Number(form.developerFee) * 100),
        ...(form.treasuryAddress.trim() ? { treasury_address: form.treasuryAddress.trim() } : {}),
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
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-text-primary)', marginBottom: '0.75rem' }}>
            Connect Your Wallet
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>
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

  const amt = Number(form.amountAlgo)
  const escrowAmount = isNaN(amt) ? 0 : Math.round(amt * 1_000_000)
  const platformFeeBps = Math.round(Number(form.platformFee || '2.0') * 100)
  const developerFeeBps = Math.round(Number(form.developerFee || '1.0') * 100)
  const { breakdown, display: feeDisplay } = useFeeBreakdown(
    escrowAmount,
    form.hitm,
    false,
    platformFeeBps,
    developerFeeBps
  )

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
        <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
          <Link href="/" style={{ color: 'var(--color-accent)' }}>Marketplace</Link>
          <span>/</span>
          <span>Create Bounty</span>
        </nav>
        <h1 style={{ margin: 0, fontSize: 'clamp(1.5rem, 4vw, 2rem)', fontWeight: 900, color: 'var(--color-text-primary)' }}>
          Create Bounty
        </h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--color-text-secondary)' }}>
          Post a task and escrow the reward on Algorand.{' '}
          <span style={{ color: 'var(--color-accent-2)' }}>★ Your karma: {karma}</span>
        </p>
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Bounty Details */}
        <div style={sectionStyle}>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>Bounty Details</h2>

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
            {errors.description && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.description}</span>}
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
                <span style={{ position: 'absolute', right: '0.875rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)', fontSize: '0.875rem', pointerEvents: 'none' }}>
                  ALGO
                </span>
              </div>
              {errors.amountAlgo && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.amountAlgo}</span>}
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
              {errors.deadlineRounds && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.deadlineRounds}</span>}
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
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
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>Repository</h2>

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
            {errors.repoUrl && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.repoUrl}</span>}
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
              <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                Human-in-the-Middle (HITM) Mode
              </h2>
              <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
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
                background: form.hitm ? 'var(--color-accent)' : 'rgba(255,255,255,0.1)',
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

        {/* Advanced Settings Accordion */}
        <div style={sectionStyle}>
          <button
            type="button"
            id="advanced-settings-toggle"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-text-primary)',
              fontSize: '1rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              padding: 0,
              textAlign: 'left',
            }}
          >
            <span>Advanced Settings</span>
            <span style={{ transform: showAdvanced ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
              ▶
            </span>
          </button>

          {showAdvanced && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '0.5rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div style={fieldStyle}>
                  <label htmlFor="platformFee" style={labelStyle}>Custom Platform Fee (%)</label>
                  <input
                    id="platformFee"
                    type="number"
                    step="0.1"
                    value={form.platformFee}
                    onChange={(e) => set('platformFee', e.target.value)}
                    style={inputStyle}
                  />
                  {errors.platformFee && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.platformFee}</span>}
                </div>

                <div style={fieldStyle}>
                  <label htmlFor="developerFee" style={labelStyle}>Custom Developer Fee (%)</label>
                  <input
                    id="developerFee"
                    type="number"
                    step="0.1"
                    value={form.developerFee}
                    onChange={(e) => set('developerFee', e.target.value)}
                    style={inputStyle}
                  />
                  {errors.developerFee && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.developerFee}</span>}
                </div>
              </div>

              <div style={fieldStyle}>
                <label htmlFor="treasuryAddress" style={labelStyle}>Custom Treasury Address</label>
                <input
                  id="treasuryAddress"
                  type="text"
                  placeholder="Algorand Address (58 chars)"
                  value={form.treasuryAddress}
                  onChange={(e) => set('treasuryAddress', e.target.value)}
                  style={inputStyle}
                />
                {errors.treasuryAddress && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.treasuryAddress}</span>}
              </div>
            </div>
          )}
        </div>

        {/* Preview & Fee Breakdown */}
        {form.amountAlgo && Number(form.amountAlgo) > 0 ? (
          <div
            style={{
              padding: '1.5rem',
              borderRadius: '1rem',
              background: 'rgba(99,102,241,0.06)',
              border: '1px solid rgba(99,102,241,0.15)',
              fontSize: '0.9375rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div>
              <strong>Escrow amount:</strong> {form.amountAlgo} ALGO{' '}
              <span style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                · Locked on-chain until completion
              </span>
            </div>
            <FeeBreakdownTable
              fee={breakdown}
              display={feeDisplay}
              hitm={form.hitm}
              label="Preview of fee breakdown"
            />
          </div>
        ) : (
          <div
            style={{
              padding: '1rem 1.25rem',
              borderRadius: '0.75rem',
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.08)',
              fontSize: '0.875rem',
              color: 'var(--color-text-muted)',
            }}
          >
            Enter a reward amount to preview the fee breakdown.
          </div>
        )}

        {/* P2P Tax Disclaimer Checkbox */}
        <div style={{ ...sectionStyle, background: 'rgba(239,68,68,0.03)', border: '1px solid rgba(239,68,68,0.15)' }}>
          <label style={{ display: 'flex', gap: '0.75rem', cursor: 'pointer', alignItems: 'flex-start' }}>
            <input
              id="tax-disclaimer-checkbox"
              type="checkbox"
              checked={form.taxAccepted}
              onChange={(e) => set('taxAccepted', e.target.checked)}
              style={{ marginTop: '0.25rem', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', lineHeight: '1.4' }}>
              I acknowledge that I am responsible for peer-to-peer tax reporting, compliance, and withholding obligations.
            </span>
          </label>
          {errors.taxAccepted && <span style={{ color: 'var(--color-danger)', fontSize: '0.8rem' }}>{errors.taxAccepted}</span>}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <Link href="/">
            <Button type="button" variant="ghost">Cancel</Button>
          </Link>
          <Button
            id="create-bounty-btn"
            type="submit"
            loading={loading}
            disabled={!form.taxAccepted}
          >
            🚀 Create &amp; Escrow
          </Button>
        </div>
      </form>
    </div>
  )
}
