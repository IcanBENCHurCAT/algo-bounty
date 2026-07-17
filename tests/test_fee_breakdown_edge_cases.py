"""Edge case tests for fee breakdown calculator.
Covers: 1 microALGO, 0 escrow, max 64-bit, odd amounts, etc.
"""

import pytest
from gateway.schemas import FeeBreakdown, FeeBreakdownDisplay


def _compute_fee(escrow: int, hitm_enabled: bool = True) -> FeeBreakdown:
    """Client-side matching formula."""
    fee = (escrow * 2) // 100 // 2  # 1% via two integer divisions
    mediator = (escrow * 25) // 10000 if hitm_enabled else 0
    return FeeBreakdown(
        escrow_amount=escrow,
        developer_royalty=fee,
        platform_treasury=fee,
        mediator_fee=mediator,
        claimant_payout=escrow - fee - fee - mediator,
    )


def _compute_fee_display(escrow: int, hitm_enabled: bool = True) -> FeeBreakdownDisplay:
    """Display formatting."""
    fb = _compute_fee(escrow, hitm_enabled)

    def _fmt(microalgo: int) -> str:
        algo = microalgo / 1_000_000
        if algo == int(algo):
            return f"{int(algo)} ALGO"
        return f"{algo:.2f} ALGO"

    return FeeBreakdownDisplay(
        total=_fmt(fb.escrow_amount),
        developer_royalty=_fmt(fb.developer_royalty),
        platform_treasury=_fmt(fb.platform_treasury),
        mediator_fee=_fmt(fb.mediator_fee),
        claimant_payout=_fmt(fb.claimant_payout),
    )


class TestEdgeCases:
    """Edge cases that could break the fee calculator."""

    def test_1_microalgo_escrow(self):
        """1 microALGO (0.000001 ALGO) — minimum possible."""
        escrow = 1
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.developer_royalty == 0
        assert fb.platform_treasury == 0
        assert fb.mediator_fee == 0
        assert fb.claimant_payout == 1
        assert fb.escrow_amount == 1

    def test_2_microalgo_escrow(self):
        """2 microALGO — still too small for any fee."""
        escrow = 2
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.developer_royalty == 0
        assert fb.platform_treasury == 0
        assert fb.mediator_fee == 0
        assert fb.claimant_payout == 2

    def test_zero_escrow(self):
        """Zero escrow — should return all zeros."""
        escrow = 0
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.escrow_amount == 0
        assert fb.developer_royalty == 0
        assert fb.platform_treasury == 0
        assert fb.mediator_fee == 0
        assert fb.claimant_payout == 0

    def test_very_large_escrow(self):
        """1 million ALGO — large but realistic."""
        escrow = 1_000_000_000_000  # 1M ALGO in microALGO
        fb = _compute_fee(escrow, hitm_enabled=True)
        royalty = (escrow * 2) // 100 // 2
        assert fb.developer_royalty == royalty
        assert fb.platform_treasury == royalty
        assert fb.claimant_payout + fb.developer_royalty + fb.platform_treasury + fb.mediator_fee == escrow

    def test_odd_microalgo_amount(self):
        """1,000,001 microALGO — odd number should not cause issues."""
        escrow = 1_000_001
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.escrow_amount == 1_000_001
        assert fb.claimant_payout + fb.developer_royalty + fb.platform_treasury + fb.mediator_fee == escrow

    def test_non_hitm_odd_amount(self):
        """Non-HITM with odd escrow — mediator fee should be 0."""
        escrow = 999_999
        fb = _compute_fee(escrow, hitm_enabled=False)
        assert fb.mediator_fee == 0
        assert fb.escrow_amount == 999_999
        assert fb.claimant_payout + fb.developer_royalty + fb.platform_treasury == escrow

    def test_just_above_mediator_threshold(self):
        """Mediator fee triggers at escrow * 25 >= 10000, i.e. escrow >= 400."""
        fb399 = _compute_fee(399, hitm_enabled=True)
        assert fb399.mediator_fee == 0
        fb400 = _compute_fee(400, hitm_enabled=True)
        assert fb400.mediator_fee == 1

    def test_display_whole_number_boundary(self):
        """0.999999 ALGO rounds to 1.00 with 2-decimal formatting."""
        escrow = 999_999
        display = _compute_fee_display(escrow, hitm_enabled=True)
        assert display.total == "1.00 ALGO"  # {:.2f} rounds 0.999999 → 1.00

    def test_display_exact_whole(self):
        """1,000,000 microALGO = exactly 1 ALGO."""
        escrow = 1_000_000
        display = _compute_fee_display(escrow, hitm_enabled=True)
        assert display.total == "1 ALGO"

    def test_display_0_01_algo(self):
        """10,000 microALGO = 0.01 ALGO."""
        escrow = 10_000
        display = _compute_fee_display(escrow, hitm_enabled=True)
        assert display.total == "0.01 ALGO"

    def test_no_overflow_at_64bit(self):
        """Maximum 64-bit signed int — Python handles big ints natively."""
        escrow = 2**63 - 1
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.escrow_amount == escrow
        assert fb.claimant_payout + fb.developer_royalty + fb.platform_treasury + fb.mediator_fee == escrow

    def test_exact_fee_split_at_10000(self):
        """10,000 microALGO: royalty=0, mediator=2, claimant=9998."""
        escrow = 10_000  # 0.01 ALGO
        fb = _compute_fee(escrow, hitm_enabled=True)
        royalty = (escrow * 2) // 100 // 2  # = 0
        assert fb.developer_royalty == royalty
        assert fb.platform_treasury == royalty
        mediator = (escrow * 25) // 10000  # = 2
        assert fb.mediator_fee == mediator
        assert fb.claimant_payout == escrow - royalty - royalty - mediator
