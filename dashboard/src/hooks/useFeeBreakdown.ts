/**
 * useFeeBreakdown — Client-side fee calculation matching the on-chain contract.
 *
 * Contract formula (Python):
 *   royalty = treasury = escrow * 2 // 100 // 2
 *   mediator_fee = escrow * 25 // 10000  (if HITM)
 *   claimant_payout = escrow - royalty - treasury - mediator_fee
 *
 * JS equivalent:
 *   Math.floor(Math.floor(escrow * 2 / 100) / 2)
 */

export interface FeeBreakdown {
  escrow_amount: number    // microALGO
  developer_royalty: number
  platform_treasury: number
  mediator_fee: number
  claimant_payout: number
}

export interface FeeBreakdownDisplay {
  total: string
  developer_royalty: string
  platform_treasury: string
  mediator_fee: string
  claimant_payout: string
}

/** Format microALGO for display: whole numbers as integers, sub-ALGO to 2 decimals. */
function formatAlgoDisplay(microAlgo: number): string {
  const algo = microAlgo / 1_000_000
  if (Number.isInteger(algo) || Math.round(algo * 100) === algo * 100) {
    const rounded = Math.round(algo * 100) / 100
    if (rounded === Math.floor(rounded)) {
      return `${Math.floor(rounded)} ALGO`
    }
  }
  return `${(microAlgo / 1_000_000).toFixed(2)} ALGO`
}

/**
 * Compute fee breakdown from escrow (microALGO) and HITM flag.
 * Mirrors the contract's exact integer-division logic.
 */
export function computeFeeBreakdown(
  escrowAmount: number,
  hitmEnabled: boolean,
): FeeBreakdown {
  const fee = Math.floor(Math.floor(escrowAmount * 2 / 100) / 2) // 1%
  const mediator = hitmEnabled
    ? Math.floor(escrowAmount * 25 / 10000)
    : 0
  return {
    escrow_amount: escrowAmount,
    developer_royalty: fee,
    platform_treasury: fee,
    mediator_fee: mediator,
    claimant_payout: escrowAmount - fee - fee - mediator,
  }
}

/** Generate human-readable display strings. */
export function formatFeeDisplay(fee: FeeBreakdown): FeeBreakdownDisplay {
  return {
    total: formatAlgoDisplay(fee.escrow_amount),
    developer_royalty: formatAlgoDisplay(fee.developer_royalty),
    platform_treasury: formatAlgoDisplay(fee.platform_treasury),
    mediator_fee: formatAlgoDisplay(fee.mediator_fee),
    claimant_payout: formatAlgoDisplay(fee.claimant_payout),
  }
}

/**
 * React hook: { breakdown, display } for any escrow amount.
 *
 * Usage:
 *   const { breakdown, display } = useFeeBreakdown(escrowAmount, hitmEnabled)
 */
export function useFeeBreakdown(
  escrowAmount: number,
  hitmEnabled: boolean,
): { breakdown: FeeBreakdown; display: FeeBreakdownDisplay } {
  return {
    breakdown: computeFeeBreakdown(escrowAmount, hitmEnabled),
    display: formatFeeDisplay(computeFeeBreakdown(escrowAmount, hitmEnabled)),
  }
}
