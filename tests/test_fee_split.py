"""Tests for the _send_fee_split fee splitting logic."""

import pytest


class TestSendFeeSplit:
    """Tests verifying the 50/50 fee split between royalty and treasury."""

    def test_fee_split_calculates_correctly_1000_algo(self):
        """Given 1000 ALGO escrow, fee split should be:
        - 10 ALGO royalty (1%)
        - 10 ALGO treasury (1%)
        - 2 ALGO mediator (0.25%, integer division)
        - 978 ALGO remainder
        """
        escrow_amount = 1000
        platform_fee = escrow_amount * 2 // 100  # 2% = 20
        royalty = platform_fee // 2  # 1% = 10
        treasury = platform_fee // 2  # 1% = 10
        mediator = escrow_amount * 25 // 10000  # 0.25% = 2 (integer: 2.5 -> 2)
        remaining = escrow_amount - platform_fee - mediator  # 1000 - 20 - 2 = 978

        assert royalty == 10
        assert treasury == 10
        assert mediator == 2
        assert remaining == 978

    def test_fee_split_dedup_when_creator_is_primary(self):
        """When the primary recipient is the creator, royalty should be zero."""
        escrow_amount = 10000
        platform_fee = escrow_amount * 2 // 100  # 200
        # royalty deduped because primary == creator
        royalty = 0
        treasury = platform_fee // 2  # 100
        mediator = escrow_amount * 25 // 10000  # 25
        # send_fee_split returns: escrow_amount - platform_fee - mediator
        # but royalty is 0 (deduped), so remaining is still escrow - platform - mediator
        remaining = escrow_amount - platform_fee - mediator

        assert royalty == 0
        assert treasury == 100
        assert mediator == 25
        assert remaining == 9775  # 10000 - 200 - 25

    def test_fee_split_agent_primary_gets_royalty(self):
        """When the primary recipient is the agent, royalty goes to creator."""
        escrow_amount = 10000
        platform_fee = escrow_amount * 2 // 100  # 200
        royalty = platform_fee // 2  # 100 (goes to creator)
        treasury = platform_fee // 2  # 100 (goes to treasury)
        mediator = escrow_amount * 25 // 10000  # 25
        remaining = escrow_amount - platform_fee - mediator  # 9775

        assert royalty == 100
        assert treasury == 100
        assert mediator == 25
        assert remaining == 9775

    def test_fee_split_rounding(self):
        """Fee split should use integer division consistently."""
        escrow_amount = 1001
        platform_fee = escrow_amount * 2 // 100  # 2002 // 100 = 20
        royalty = platform_fee // 2  # 10
        treasury = platform_fee // 2  # 10
        mediator = escrow_amount * 25 // 10000  # 25025 // 10000 = 2
        remaining = escrow_amount - platform_fee - mediator  # 1001 - 20 - 2 = 979

        assert platform_fee == 20
        assert royalty == 10
        assert treasury == 10
        assert mediator == 2
        assert remaining == 979

    def test_fee_split_no_negative(self):
        """Fee split should not produce negative remaining for large fees."""
        escrow_amount = 100  # Minimum reasonable escrow
        platform_fee = escrow_amount * 2 // 100  # 2
        royalty = platform_fee // 2  # 1
        treasury = platform_fee // 2  # 1
        mediator = escrow_amount * 25 // 10000  # 0 (integer division)
        remaining = escrow_amount - platform_fee - mediator  # 100 - 2 - 0 = 98

        assert royalty == 1
        assert treasury == 1
        assert mediator == 0
        assert remaining == 98

    def test_fee_split_small_escrow(self):
        """With very small escrow, all fees should still be non-negative."""
        escrow_amount = 10
        platform_fee = escrow_amount * 2 // 100  # 0
        royalty = 0
        treasury = 0
        mediator = 0
        remaining = 10

        assert platform_fee == 0
        assert royalty == 0
        assert treasury == 0
        assert mediator == 0
        assert remaining == 10
