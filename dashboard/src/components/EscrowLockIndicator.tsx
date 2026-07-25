import React from 'react'

interface EscrowLockIndicatorProps {
  status: string
}

export function EscrowLockIndicator({ status }: EscrowLockIndicatorProps) {
  if (!['submitted', 'rejected', 'disputed'].includes(status.toLowerCase())) {
    return null
  }

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
      <span>🔒</span>
      <span>Escrow Locked (Work Submitted)</span>
    </div>
  )
}
