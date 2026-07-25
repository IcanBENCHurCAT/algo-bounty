'use client'

import React from 'react'

const RULES = [
  {
    id: 1,
    title: '1. Escrow Lock',
    subtitle: 'Your Money is Protected by Code',
    badge: 'Protection for Workers',
    color: 'emerald',
    description:
      'Once work is submitted, creator refunds are locked on-chain. Creators cannot withdraw escrow funds while a submission is pending review.',
  },
  {
    id: 2,
    title: '2. 3-Rejection Revision Cap',
    subtitle: 'Fair Work Limits',
    badge: 'Protection for Workers',
    color: 'indigo',
    description:
      'Creators can request up to 3 code revisions. On the 3rd rejection, the bounty automatically escalates to DISPUTED state for independent review.',
  },
  {
    id: 3,
    title: '3. 7-Day Review Timers',
    subtitle: 'Inactivity Safeguards',
    badge: 'Protection for Both',
    color: 'amber',
    description:
      'Creator inactivity in review mode automatically releases funds to the worker. Creators must wait 7 days post-rejection before reclaiming abandoned escrow.',
  },
  {
    id: 4,
    title: '4. 30-Day Automated Timeout',
    subtitle: 'No Frozen Funds Guarantee',
    badge: 'Smart Contract Safety',
    color: 'cyan',
    description:
      'If a dispute remains inactive for 30 days, any participant can trigger a trustless 50/50 split on-chain. Funds are never permanently stuck.',
  },
  {
    id: 5,
    title: '5. 72-Hour Account Quarantine',
    subtitle: 'Zero-Tolerance Fraud Defense',
    badge: 'Anti-Theft Defense',
    color: 'rose',
    description:
      'Merging a pull request post-refund triggers an immediate 72-hour account quarantine, admin review, and a -100 Karma penalty.',
  },
  {
    id: 6,
    title: '6. Sync with GitHub Fallback',
    subtitle: 'Webhook Reliability Backup',
    badge: 'System Reliability',
    color: 'violet',
    description:
      'If webhooks drop, manual sync endpoints verify PR status directly against GitHub API with full idempotency guarantees.',
  },
]

export function RulesOfGame() {
  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-slate-100">Rules of the Game & Safety Guarantees</h2>
        </div>
        <p className="text-xs text-slate-400">
          How smart contract mechanisms keep every bounty safe, fair, and transparent.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {RULES.map((r) => (
          <div
            key={r.id}
            className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 hover:border-slate-700 transition-colors shadow"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {r.badge}
              </span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">{r.title}</h3>
              <p className="text-xs font-medium text-slate-400">{r.subtitle}</p>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">{r.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
