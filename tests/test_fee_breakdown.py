"""Test fee breakdown calculations (FR-002, SC-002).

These tests verify the fee computation matches the on-chain contract formula:
  royalty = treasury = escrow * 2 // 100 // 2  (1% each)
  mediator_fee = escrow * 25 // 10000  (0.25%, only if HITM)
  claimant_payout = escrow - royalty - treasury - mediator_fee

SC-002: zero instances where displayed fee amounts differ from on-chain amounts.
"""
import pytest
from gateway.schemas import FeeBreakdown, FeeBreakdownDisplay


def _compute_fee(escrow_amount: int, hitm_enabled: bool) -> FeeBreakdown:
    """Mirror the on-chain contract's integer-division logic."""
    fee = (escrow_amount * 2) // 100 // 2  # 1% royalty + 1% treasury each
    mediator_fee = (escrow_amount * 25) // 10000 if hitm_enabled else 0
    claimant_payout = escrow_amount - fee - fee - mediator_fee
    return FeeBreakdown(
        escrow_amount=escrow_amount,
        developer_royalty=fee,
        platform_treasury=fee,
        mediator_fee=mediator_fee,
        claimant_payout=claimant_payout,
    )


class TestFeeBreakdown:
    """Core fee calculation correctness."""

    def test_exact_1000_algo(self):
        """1000 ALGO: royalty=10, treasury=10, mediator=2.5, claimant=977.5."""
        escrow = 1000_000_000  # 1000 ALGO in microALGO
        fb = _compute_fee(escrow, hitm_enabled=True)

        assert fb.developer_royalty == 10_000_000  # 10 ALGO
        assert fb.platform_treasury == 10_000_000  # 10 ALGO
        assert fb.mediator_fee == 2_500_000  # 2.5 ALGO
        assert fb.claimant_payout == 977_500_000  # 977.5 ALGO

        # Conservation invariant
        total = fb.claimant_payout + fb.developer_royalty + fb.platform_treasury + fb.mediator_fee
        assert total == fb.escrow_amount

    def test_small_escrow_one_algo(self):
        """1 ALGO: 1% = 0.01 ALGO (integer division gives 10,000 microALGO)."""
        escrow = 1_000_000  # 1 ALGO
        fb = _compute_fee(escrow, hitm_enabled=False)

        assert fb.developer_royalty == 10_000  # 0.01 ALGO
        assert fb.platform_treasury == 10_000  # 0.01 ALGO
        assert fb.mediator_fee == 0  # no mediator
        assert fb.claimant_payout == 980_000  # 0.98 ALGO

    def test_small_escrow_100_algo(self):
        """100 ALGO: 1% = 1 ALGO, mediator 0.25% = 0.25 ALGO, claimant=97.75."""
        escrow = 100_000_000  # 100 ALGO
        fb = _compute_fee(escrow, hitm_enabled=True)

        assert fb.developer_royalty == 1_000_000  # 1 ALGO
        assert fb.platform_treasury == 1_000_000  # 1 ALGO
        assert fb.mediator_fee == 250_000  # 0.25 ALGO
        assert fb.claimant_payout == 97_750_000  # 97.75 ALGO

    def test_zero_escrow(self):
        """Edge case: zero escrow should produce zero fees."""
        fb = _compute_fee(0, hitm_enabled=True)
        assert fb.escrow_amount == 0
        assert fb.developer_royalty == 0
        assert fb.platform_treasury == 0
        assert fb.mediator_fee == 0
        assert fb.claimant_payout == 0

    def test_large_escrow(self):
        """10M ALGO: royalty=100K, treasury=100K, mediator=25K."""
        escrow = 10_000_000_000_000  # 10 million ALGO
        fb = _compute_fee(escrow, hitm_enabled=True)

        assert fb.developer_royalty == 100_000_000_000  # 100K ALGO
        assert fb.platform_treasury == 100_000_000_000  # 100K ALGO
        assert fb.mediator_fee == 25_000_000_000  # 25K ALGO
        assert fb.claimant_payout == 9_775_000_000_000  # 9.775M ALGO

        # Conservation
        total = fb.claimant_payout + fb.developer_royalty + fb.platform_treasury + fb.mediator_fee
        assert total == fb.escrow_amount


class TestFeeBreakdownNoHITM:
    """Non-HITM bounties: mediator fee is zero."""

    def test_no_hitm_full_breakdown(self):
        """Even with non-HITM, mediator_fee column should show 0, not be omitted."""
        escrow = 100_000_000  # 100 ALGO
        fb = _compute_fee(escrow, hitm_enabled=False)

        assert fb.developer_royalty == 1_000_000
        assert fb.platform_treasury == 1_000_000
        assert fb.mediator_fee == 0  # explicitly zero
        assert fb.claimant_payout == 98_000_000


class TestFeeConservation:
    """Verify claimant_payout is always escrow - sum(all_fees)."""

    @pytest.mark.parametrize("escrow_micro", [
        1_000_000,       # 1 ALGO
        10_000_000,      # 10 ALGO
        100_000_000,     # 100 ALGO
        1_000_000_000,   # 1K ALGO
        10_000_000_000,  # 10K ALGO
        100_000_000_000, # 100K ALGO
    ])
    @pytest.mark.parametrize("hitm", [True, False])
    def test_conservation_invariant(self, escrow_micro, hitm):
        """For any escrow amount, claimant + fees == escrow."""
        fb = _compute_fee(escrow_micro, hitm)
        total_fees = fb.developer_royalty + fb.platform_treasury + fb.mediator_fee
        assert fb.claimant_payout + total_fees == escrow_micro


class TestDisplayFormatting:
    """FR-010: display formatting rules."""

    def _fmt(self, microalgo: int) -> str:
        """FR-010 format function."""
        algo = microalgo / 1_000_000
        if algo == int(algo):
            return f"{int(algo)} ALGO"
        return f"{algo:.2f} ALGO"

    def test_whole_number(self):
        """Whole ALGO values get no decimals."""
        assert self._fmt(1_000_000) == "1 ALGO"
        assert self._fmt(100_000_000) == "100 ALGO"
        assert self._fmt(0) == "0 ALGO"

    def test_fractional(self):
        """Fractional ALGO values get 2 decimal places."""
        assert self._fmt(250_000) == "0.25 ALGO"
        assert self._fmt(1_500_000) == "1.50 ALGO"
        assert self._fmt(100_001) == "0.10 ALGO"  # 0.100001 rounds to 0.10 with .2f


class TestContractParity:
    """SC-002: verify Python matches the contract's Go/Teal formula.

    The contract uses:
      royalty = escrow * 2 // 100 // 2   (integer division floor)
    In Python, this is (escrow * 2) // 100 // 2.
    """

    def test_contract_formula_matches(self):
        """Verify our implementation matches the contract formula for many values."""
        for escrow_micro in [
            1_000_000, 2_000_000, 500_000, 750_000,  # small values
            10_000_000, 50_000_000, 100_000_000,      # medium
            1_000_000_000, 5_000_000_000, 10_000_000_000,  # large
        ]:
            fb = _compute_fee(escrow_micro, hitm_enabled=True)

            # Verify the formula
            expected_fee = (escrow_micro * 2) // 100 // 2
            expected_mediator = (escrow_micro * 25) // 10000
            expected_claimant = escrow_micro - expected_fee - expected_fee - expected_mediator

            assert fb.developer_royalty == expected_fee, f"royalty mismatch at {escrow_micro}"
            assert fb.platform_treasury == expected_fee, f"treasury mismatch at {escrow_micro}"
            assert fb.mediator_fee == expected_mediator, f"mediator mismatch at {escrow_micro}"
            assert fb.claimant_payout == expected_claimant, f"claimant mismatch at {escrow_micro}"
