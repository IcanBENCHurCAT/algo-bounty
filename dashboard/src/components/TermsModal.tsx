'use client'

import React, { useEffect, useRef, useState, useSyncExternalStore } from 'react'

const subscribeStorage = (onStoreChange: () => void) => {
  window.addEventListener('storage', onStoreChange)
  return () => window.removeEventListener('storage', onStoreChange)
}

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function TermsModal() {
  const [dismissed, setDismissed] = useState(false)
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const needsAcceptance = useSyncExternalStore(
    subscribeStorage,
    () => !localStorage.getItem('algobounty_tos_accepted'),
    () => false,
  )
  const isOpen = !dismissed && needsAcceptance

  useEffect(() => {
    if (!isOpen) return

    const dialog = dialogRef.current
    if (!dialog) return

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    dialog.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
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

    // Intentionally do not dismiss on Escape: Terms acceptance is mandatory.
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      if (previousFocusRef.current?.isConnected) {
        previousFocusRef.current.focus()
      }
    }
  }, [isOpen])

  const handleAccept = () => {
    localStorage.setItem('algobounty_tos_accepted', 'true')
    setDismissed(true)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="terms-modal-title"
        aria-describedby="terms-modal-description"
        tabIndex={-1}
        className="max-w-xl w-full p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl space-y-5 text-slate-200 outline-none"
      >
        <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <svg aria-hidden="true" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h2 id="terms-modal-title" className="text-xl font-bold text-slate-100">Terms of Service & Legal Notice</h2>
            <p className="text-xs text-slate-400">Pre-Mainnet Protocol Stewardship Notice</p>
          </div>
        </div>

        <div
          id="terms-modal-description"
          tabIndex={0}
          className="space-y-3 text-xs text-slate-300 max-h-60 overflow-y-auto pr-2 leading-relaxed focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-400 rounded-lg"
        >
          <p>
            <strong>1. Non-Custodial Software Protocol:</strong> AlgoBounty is an open-source, non-custodial smart contract protocol. Funds deposited into bounties are locked directly in Algorand smart contract Box storage and are governed exclusively by on-chain state machine rules.
          </p>
          <p>
            <strong>2. Phase 1 Admin Stewardship:</strong> During the Phase 1 Pre-Mainnet phase, administrative oversight is provided on a best-effort basis for dispute resolution and abuse prevention (e.g. account quarantines). Administrative resolution does not constitute financial custody, escrow bailment, or an admission of legal liability.
          </p>
          <p>
            <strong>3. Counterparty Compliance & Taxes:</strong> Bounties represent direct peer-to-peer engagements between task creators and independent workers. All tax reporting, legal compliance, and work authorization remain the sole responsibility of the respective counterparties.
          </p>
          <p>
            <strong>4. Mandatory Arbitration:</strong> By accepting these terms, you agree to resolve any dispute arising from software usage through binding arbitration under the Federal Arbitration Act (FAA) and waive any right to participate in class actions.
          </p>
        </div>

        <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
          <span className="text-xs text-slate-500">Version 1.0.0 (Pre-Mainnet)</span>
          <button
            type="button"
            onClick={handleAccept}
            className="px-5 py-2.5 text-xs font-semibold text-slate-950 bg-indigo-400 hover:bg-indigo-300 rounded-xl transition-colors inline-flex items-center gap-2 shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-300"
          >
            Accept & Continue
          </button>
        </div>
      </div>
    </div>
  )
}
