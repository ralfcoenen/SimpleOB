"""Tests für die Ergebnisverwendungswerte der Taxonomie 6.9."""

from decimal import Decimal

from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_profit_appropriation_values import (
    GaapCi69ProfitAppropriationValueBuilder,
)


def test_builds_profit_appropriation_values() -> None:
    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("500.00"),
        other_revenue_reserves_addition=Decimal("1000.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("3500.00"),
        profit_loss_carryforward=Decimal("7000.00"),
    )

    values = GaapCi69ProfitAppropriationValueBuilder.build(
        net_income=Decimal("10000.00"),
        previous_profit_loss_carryforward=Decimal("2000.00"),
        data=data,
    )

    assert values == {
        (
            "incomeUse.gainLoss",
        ): Decimal("0.00"),
        (
            "incomeUse.gainLoss.netIncome",
        ): Decimal("10000.00"),
        (
            "incomeUse.gainLoss.retainedEarningsPrevYear",
        ): Decimal("2000.00"),
        (
            "incomeUse.gainLoss.additionRevenReserves",
        ): Decimal("1500.00"),
        (
            "incomeUse.gainLoss."
            "additionRevenReserves.legalRes",
        ): Decimal("500.00"),
        (
            "incomeUse.gainLoss.additionOtherRes",
        ): Decimal("1000.00"),
        (
            "incomeUse.gainLoss.dividensPlanned",
        ): Decimal("3500.00"),
        (
            "incomeUse.gainLoss.additionRetainedEarnings",
        ): Decimal("7000.00"),
    }


def test_builds_loss_appropriation_with_reserve_release() -> None:
    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("0.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("1000.00"),
        other_revenue_reserves_release=Decimal("2000.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("-5000.00"),
    )

    values = GaapCi69ProfitAppropriationValueBuilder.build(
        net_income=Decimal("-8000.00"),
        previous_profit_loss_carryforward=Decimal("0.00"),
        data=data,
    )

    assert values == {
        (
            "incomeUse.gainLoss",
        ): Decimal("0.00"),
        (
            "incomeUse.gainLoss.netIncome",
        ): Decimal("-8000.00"),
        (
            "incomeUse.gainLoss.releaseRevenReserves",
        ): Decimal("3000.00"),
        (
            "incomeUse.gainLoss."
            "releaseRevenReserves.legalRes",
        ): Decimal("1000.00"),
        (
            "incomeUse.gainLoss.releaseOtherRes",
        ): Decimal("2000.00"),
        (
            "incomeUse.gainLoss.additionCummLoss",
        ): Decimal("5000.00"),
    }


def test_splits_previous_loss_carryforward() -> None:
    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("0.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("-3000.00"),
    )

    values = GaapCi69ProfitAppropriationValueBuilder.build(
        net_income=Decimal("2000.00"),
        previous_profit_loss_carryforward=Decimal("-5000.00"),
        data=data,
    )

    assert values == {
        (
            "incomeUse.gainLoss",
        ): Decimal("0.00"),
        (
            "incomeUse.gainLoss.netIncome",
        ): Decimal("2000.00"),
        (
            "incomeUse.gainLoss.accumLossPrevYear",
        ): Decimal("5000.00"),
        (
            "incomeUse.gainLoss.additionCummLoss",
        ): Decimal("3000.00"),
    }
