"""Tests für die BVV-FactPlan-Werte."""

from decimal import Decimal

from openbilanz.eric.bilanz_generation.bvv_value_builder import (
    BvvValueBuilder,
)


def test_builds_first_year_bvv_values() -> None:
    values = BvvValueBuilder.build(
        current_hgb_equity=Decimal("13868.35"),
        previous_hgb_equity=Decimal("0.00"),
        current_book_value_difference=Decimal("83.33"),
        previous_book_value_difference=Decimal("0.00"),
        contribution=Decimal("10000.00"),
        withdrawal_distribution=Decimal("0.00"),
    )

    assert values == {
        ("BVV.profitLoss",): Decimal("3951.68"),
        (
            "BVV.profitLoss.assetsCurrentYear",
        ): Decimal("13951.68"),
        (
            "BVV.profitLoss.assetsPreviousYear",
        ): Decimal("0.00"),
        (
            "BVV.profitLoss.assetsPreviousYear.assets",
        ): Decimal("0.00"),
        (
            "BVV.profitLoss.assetsPreviousYear.capAdjustments",
        ): Decimal("0.00"),
        (
            "BVV.profitLoss.withdrawalDistrib",
        ): Decimal("0.00"),
        (
            "BVV.profitLoss.contribution",
        ): Decimal("10000.00"),
    }


def test_builds_follow_up_year_bvv_values() -> None:
    values = BvvValueBuilder.build(
        current_hgb_equity=Decimal("13535.02"),
        previous_hgb_equity=Decimal("13868.35"),
        current_book_value_difference=Decimal("83.33"),
        previous_book_value_difference=Decimal("83.33"),
        contribution=Decimal("0.00"),
        withdrawal_distribution=Decimal("0.00"),
    )

    assert values == {
        ("BVV.profitLoss",): Decimal("-250.00"),
        (
            "BVV.profitLoss.assetsCurrentYear",
        ): Decimal("13701.68"),
        (
            "BVV.profitLoss.assetsPreviousYear",
        ): Decimal("13951.68"),
        (
            "BVV.profitLoss.assetsPreviousYear.assets",
        ): Decimal("13951.68"),
        (
            "BVV.profitLoss.assetsPreviousYear.capAdjustments",
        ): Decimal("0.00"),
        (
            "BVV.profitLoss.withdrawalDistrib",
        ): Decimal("0.00"),
        (
            "BVV.profitLoss.contribution",
        ): Decimal("0.00"),
    }
