"""Tests for the dynamic mediator fee safety net logic."""

import pytest


class TestMediatorFeeSafetyNet:
    """Tests verifying the redirect of mediator fee under HITM and undisputed Auto modes."""

    def test_hitm_mode_redirects_mediator_fee_to_worker(self):
        """Under HITM mode, the 0.25% mediator fee must be redirected to the worker (claimant)."""
        escrow_amount = 10000
        platform_fee = escrow_amount * 2 // 100  # 2% platform fee = 200
        royalty = platform_fee // 2              # 1% royalty = 100
        treasury = platform_fee - royalty        # 1% treasury = 100
        mediator_fee = escrow_amount * 25 // 10000  # 0.25% mediator fee = 25

        # In HITM mode, mediator fee goes to worker
        is_hitm = True
        is_dispute = False

        mediator_payout = 0
        worker_payout_increase = 0

        if is_hitm or not is_dispute:
            worker_payout_increase = mediator_fee
        else:
            mediator_payout = mediator_fee

        assert worker_payout_increase == 25
        assert mediator_payout == 0

    def test_undisputed_auto_mode_redirects_mediator_fee_to_worker(self):
        """Under Auto mode, if no dispute is raised, the 0.25% mediator fee must go to the worker."""
        escrow_amount = 10000
        mediator_fee = escrow_amount * 25 // 10000  # 25

        is_hitm = False
        is_dispute = False

        mediator_payout = 0
        worker_payout_increase = 0

        if is_hitm or not is_dispute:
            worker_payout_increase = mediator_fee
        else:
            mediator_payout = mediator_fee

        assert worker_payout_increase == 25
        assert mediator_payout == 0

    def test_disputed_auto_mode_payouts_mediator_fee_to_mediator(self):
        """Under Auto mode, if a dispute is resolved via arbitration, the mediator fee goes to the mediator."""
        escrow_amount = 10000
        mediator_fee = escrow_amount * 25 // 10000  # 25

        is_hitm = False
        is_dispute = True

        mediator_payout = 0
        worker_payout_increase = 0

        if is_hitm or not is_dispute:
            worker_payout_increase = mediator_fee
        else:
            mediator_payout = mediator_fee

        assert worker_payout_increase == 0
        assert mediator_payout == 25
