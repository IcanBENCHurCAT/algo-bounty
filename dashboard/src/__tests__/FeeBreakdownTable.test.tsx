/** @jest-environment jsdom */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FeeBreakdownTable } from '../components/ui/FeeBreakdownTable';

describe('FeeBreakdownTable', () => {
  const fee = {
    escrow_amount: 1_000_000_000, // 1000 ALGO
    developer_royalty: 10_000_000,
    platform_treasury: 10_000_000,
    mediator_fee: 2_500_000,
    claimant_payout: 977_500_000,
  };

  const display = {
    total: '1000 ALGO',
    developer_royalty: '0.1 ALGO',
    platform_treasury: '0.1 ALGO',
    mediator_fee: '0.25 ALGO',
    claimant_payout: '977.5 ALGO',
  };

  it('renders the label correctly (HITM)', () => {
    render(<FeeBreakdownTable fee={fee} display={display} hitm={true} label="Test Fee Breakdown" />);
    expect(screen.getByRole('group')).toHaveAttribute('aria-label', 'Test Fee Breakdown');
  });

  it('renders all rows including mediator fee for HITM', () => {
    render(<FeeBreakdownTable fee={fee} display={display} hitm={true} label="Test" />);
    expect(screen.getByText('Total Released')).toBeInTheDocument();
    expect(screen.getByText('1000 ALGO')).toBeInTheDocument();
    expect(screen.getByText('Developer Royalty (1%)')).toBeInTheDocument();
    expect(screen.getByText('Platform Treasury (1%)')).toBeInTheDocument();
    expect(screen.getByText('Mediator Fee (0.25%)')).toBeInTheDocument();
    expect(screen.getByText('0.25 ALGO')).toBeInTheDocument();
    expect(screen.getByText('Claimant Payout')).toBeInTheDocument();
    expect(screen.getByText('977.5 ALGO')).toBeInTheDocument();
  });

  it('shows "0 ALGO" for mediator fee when HITM but mediator_fee is 0', () => {
    const feeZeroMediator = { ...fee, mediator_fee: 0 };
    const displayZeroMediator = { ...display, mediator_fee: '0 ALGO' };
    render(<FeeBreakdownTable fee={feeZeroMediator} display={displayZeroMediator} hitm={true} label="Test" />);
    expect(screen.getByText('Mediator Fee (0.25%)')).toBeInTheDocument();
    // Should show "0 ALGO" not "Not applicable"
    expect(screen.getByText('0 ALGO')).toBeInTheDocument();
  });

  it('shows "Not applicable" for mediator fee when not HITM', () => {
    const displayNotApplicable = { ...display, mediator_fee: 'N/A' };
    render(<FeeBreakdownTable fee={fee} display={displayNotApplicable} hitm={false} label="Test" />);
    expect(screen.getByText('Mediator Fee (0.25%)')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<FeeBreakdownTable fee={fee} display={display} hitm={true} label="Custom Label" />);
    expect(screen.getByRole('group')).toHaveAttribute('aria-label', 'Custom Label');
  });
});
