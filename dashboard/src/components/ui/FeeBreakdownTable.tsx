'use client'

/**
 * FeeBreakdownTable — Accessible, responsive fee breakdown table.
 *
 * WCAG 2.1 AA:
 * - role="table" with aria-label for screen readers
 * - row headers (scope="row") for each line item
 * - Color contrast ≥ 4.5:1 for all text
 * - Responsive layout at ≤480px (stacked rows)
 *
 * FR-002, FR-010, SC-002
 */

import { FeeBreakdownDisplay, FeeBreakdown } from '@/types'

interface FeeBreakdownTableProps {
  fee: FeeBreakdown
  display: FeeBreakdownDisplay
  hitm: boolean
  label?: string
}

export function FeeBreakdownTable({
  fee,
  display,
  hitm,
  label = 'Fee Breakdown',
}: FeeBreakdownTableProps) {
  const rows = [
    {
      label: 'Total Released',
      amount: display.total,
      strong: true,
      borderBottom: true,
    },
    {
      label: 'Developer Royalty (1%)',
      amount: display.developer_royalty,
      color: '#6ee7b7',
      borderBottom: true,
    },
    {
      label: 'Platform Treasury (1%)',
      amount: display.platform_treasury,
      color: '#94a3b8',
      borderBottom: true,
    },
    {
      label: 'Mediator Fee (0.25%)',
      amount: display.mediator_fee,
      color: fee.mediator_fee > 0 ? '#94a3b8' : undefined,
      borderBottom: true,
      variant: hitm ? (fee.mediator_fee > 0 ? 'active' : 'zero') : 'not-applicable',
    },
    {
      label: 'Claimant Payout',
      amount: display.claimant_payout,
      strong: true,
      boldLabel: true,
      largeAmount: true,
    },
  ]

  return (
    <div role="group" aria-label={label} style={{ width: '100%' }}>
      {/* Responsive: at ≤480px, use stacked card layout instead of table */}
      <style>{`
        @media (max-width: 480px) {
          .fee-table-wrapper table, .fee-table-wrapper thead, .fee-table-wrapper tbody, .fee-table-wrapper th, .fee-table-wrapper td, .fee-table-wrapper tr {
            display: block;
          }
          .fee-table-wrapper thead {
            position: absolute;
            width: 1px;
            height: 1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
          }
          .fee-table-wrapper tbody tr {
            margin-bottom: 0.75rem;
            padding: 0.5rem 0;
          }
          .fee-table-wrapper td {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.375rem 0;
          }
        }
      `}</style>
      <div className="fee-table-wrapper">
        {/* Desktop table */}
        <table
          role="table"
          aria-label={label}
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '0.9375rem',
            marginBottom: '1.25rem',
            display: 'table',
          }}
        >
        <thead>
          <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
            <th
              scope="col"
              style={{
                padding: '0.5rem 0.75rem 0.5rem 0',
                color: '#94a3b8',
                fontWeight: 500,
                width: '60%',
              }}
            >
              Item
            </th>
            <th
              scope="col"
              style={{
                padding: '0.5rem 0 0.5rem 0.75rem',
                color: '#94a3b8',
                fontWeight: 500,
                textAlign: 'right',
                width: '40%',
              }}
            >
              Amount
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              style={{
                borderBottom: row.borderBottom ? '1px solid rgba(255,255,255,0.06)' : 'none',
              }}
            >
              <td
                scope="row"
                style={{
                  padding: '0.625rem 0.75rem 0.625rem 0',
                  color: row.color || (row.variant === 'not-applicable' ? '#64748b' : undefined),
                  fontWeight: row.boldLabel ? 600 : 400,
                  fontStyle: row.variant === 'not-applicable' ? 'italic' : undefined,
                  fontSize: row.variant === 'not-applicable' ? '0.9375rem' : undefined,
                }}
              >
                {row.label}
              </td>
              <td
                style={{
                  padding: '0.625rem 0 0.625rem 0.75rem',
                  textAlign: 'right',
                  fontWeight: row.strong ? (row.largeAmount ? 700 : 600) : 400,
                  color: row.color,
                  fontSize: row.largeAmount ? '1.0625rem' : '0.9375rem',
                }}
              >
                {row.amount}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  )
}
