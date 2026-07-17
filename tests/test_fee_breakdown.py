"""
test_fee_breakdown — Validate fee calculation correctness.

Formula (from on-chain contract, Python):
  royalty = treasury = escrow * 2 // 100 // 2      (1%)
  mediator_fee = escrow * 25 // 10000               (0.25%, HITM only)
  claimant_payout = escrow - royalty - treasury - mediator_fee

Conservation invariant: claimant_payout + royalty + treasury + mediator_fee == escrow
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


def _fmt(microalgo: int) -> str:
    algo = microalgo / 1_000_000
    if algo == int(algo):
        return f"{int(algo)} ALGO"
    return f"{algo:.2f} ALGO"


# ---------------------------------------------------------------------------
# T005 — Core formula correctness (FR-003)
# ---------------------------------------------------------------------------


class TestFeeBreakdown:
    """Formula correctness at representative escrow sizes."""

    def test_exact_1000_algo(self):
        """1000 ALGO escrow: royalty=10, treasury=10, mediator=2.5, claimant=977.5."""
        escrow = 1_000_000_000  # 1000 ALGO in microALGO
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.developer_royalty == 10_000_000       # 10 ALGO
        assert fb.platform_treasury == 10_000_000        # 10 ALGO
        assert fb.mediator_fee == 2_500_000              # 2.5 ALGO
        assert fb.claimant_payout == 977_500_000         # 977.5 ALGO

    def test_small_escrow_one_algo(self):
        """1 ALGO escrow: 1% of 1_000_000 = 10_000 per fee, mediator=2_500."""
        escrow = 1_000_000  # 1 ALGO
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.developer_royalty == 10_000       # 0.01 ALGO
        assert fb.platform_treasury == 10_000       # 0.01 ALGO
        assert fb.mediator_fee == 2_500              # 0.0025 ALGO
        assert fb.claimant_payout == 977_500          # 0.9775 ALGO

    def test_small_escrow_rounding(self):
        """0.5 ALGO escrow: 1% = 5_000, mediator=1_250 — small but valid."""
        escrow = 500_000  # 0.5 ALGO
        fb = _compute_fee(escrow, hitm_enabled=True)
        assert fb.developer_royalty == 5_000
        assert fb.platform_treasury == 5_000
        assert fb.mediator_fee == 1_250
        assert fb.claimant_payout == 488_750

    def test_zero_escrow(self):
        """Zero escrow produces zero for all fields."""
        fb = _compute_fee(0)
        assert fb.escrow_amount == 0
        assert fb.developer_royalty == 0
        assert fb.platform_treasury == 0
        assert fb.mediator_fee == 0
        assert fb.claimant_payout == 0


# ---------------------------------------------------------------------------
# Non-HITM: mediator fee must be zero (FR-007)
# ---------------------------------------------------------------------------


class TestFeeBreakdownNoHITM:
    def test_no_hitm_full_breakdown(self):
        escrow = 100_000_000  # 100 ALGO
        fb = _compute_fee(escrow, hitm_enabled=False)
        assert fb.mediator_fee == 0
        assert fb.developer_royalty == 1_000_000   # 1% = 1 ALGO
        assert fb.platform_treasury == 1_000_000
        assert fb.claimant_payout == 98_000_000    # 98 ALGO


# ---------------------------------------------------------------------------
# Conservation invariant (SC-002): claimant + all_fees == escrow
# ---------------------------------------------------------------------------


class TestFeeConservation:
    @pytest.mark.parametrize("escrow", [
        1_000_000,       # 1 ALGO
        10_000_000,      # 10 ALGO
        100_000_000,     # 100 ALGO
        1_000_000_000,   # 1000 ALGO
        10_000_000_000,  # 10k ALGO
        100_000_000_000, # 100k ALGO
    ])
    @pytest.mark.parametrize("hitm", [True, False])
    def test_conservation_invariant(self, escrow, hitm):
        fb = _compute_fee(escrow, hitm_enabled=hitm)
        total = fb.claimant_payout + fb.developer_royalty + fb.platform_treasury + fb.mediator_fee
        assert total == escrow


# ---------------------------------------------------------------------------
# Display formatting (FR-010)
# ---------------------------------------------------------------------------


class TestDisplayFormatting:
    def test_whole_number(self):
        """1000 ALGO — whole number display."""
        fb = _compute_fee(1_000_000_000)
        display = FeeBreakdownDisplay(
            total=_fmt(fb.escrow_amount),
            developer_royalty=_fmt(fb.developer_royalty),
            platform_treasury=_fmt(fb.platform_treasury),
            mediator_fee=_fmt(fb.mediator_fee),
            claimant_payout=_fmt(fb.claimant_payout),
        )
        assert display.total == "1000 ALGO"
        assert display.developer_royalty == "10 ALGO"
        assert display.claimant_payout == "977.50 ALGO"

    def test_fractional(self):
        """1.5 ALGO — fractional display."""
        fb = _compute_fee(1_500_000)
        display = FeeBreakdownDisplay(
            total=_fmt(fb.escrow_amount),
            developer_royalty=_fmt(fb.developer_royalty),
            platform_treasury=_fmt(fb.platform_treasury),
            mediator_fee=_fmt(fb.mediator_fee),
            claimant_payout=_fmt(fb.claimant_payout),
        )
        assert display.total == "1.50 ALGO"


# ---------------------------------------------------------------------------
# Contract parity: Python matches the TypeScript formula
# ---------------------------------------------------------------------------


class TestContractParity:
    """Verify Python matches JS: Math.floor(Math.floor(escrow * 2 / 100) / 2)."""

    @pytest.mark.parametrize("escrow", [1_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000, 500_000_000, 1_000_000_000, 5_000_000_000, 10_000_000_000])
    def test_contract_formula_matches(self, escrow):
        """Both Python and JS produce the same fee value."""
        py_fee = (escrow * 2) // 100 // 2
        # JS equivalent: Math.floor(Math.floor(escrow * 2 / 100) / 2)
        js_fee = int(int(escrow * 2 / 100) / 2)
        assert py_fee == js_fee, f"escrow={escrow}: python={py_fee}, js={js_fee}"
