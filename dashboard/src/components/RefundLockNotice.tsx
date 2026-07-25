import React from 'react'

export function RefundLockNotice() {
  return (
    <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm flex items-start gap-3 my-4">
      <span className="text-xl">🔒</span>
      <div>
        <h4 className="font-semibold text-amber-100">Escrow Refund Lock Policy</h4>
        <p className="mt-1 text-xs text-amber-200/80">
          Once a worker submits work on this bounty, escrowed funds are locked and cannot be unilaterally refunded by the creator. You must approve, reject, or escalate to formal dispute.
        </p>
      </div>
    </div>
  )
}
