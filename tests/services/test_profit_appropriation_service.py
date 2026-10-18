"""Tests für den ProfitAppropriationService."""

from datetime import date
from decimal import Decimal

from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.reporting.trial_balance_report import (
    TrialBalanceReport,
    TrialBalanceReportRow,
)
from simpleob.services.profit_appropriation_service import (
    ProfitAppropriationService,
)


def test_profit_appropriation_is_consistent_for_profit() -> None:
    service = ProfitAppropriationService()

    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("500.00"),
        other_revenue_reserves_addition=Decimal("1000.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("3500.00"),
        profit_loss_carryforward=Decimal("7000.00"),
    )

    result = service.validate(
        net_income=Decimal("10000.00"),
        previous_profit_loss_carryforward=Decimal("2000.00"),
        data=data,
    )

    assert result.is_consistent
    assert result.errors == ()


def test_profit_appropriation_is_consistent_for_loss_with_reserve_release() -> None:
    service = ProfitAppropriationService()

    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("0.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("3000.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("-5000.00"),
    )

    result = service.validate(
        net_income=Decimal("-8000.00"),
        previous_profit_loss_carryforward=Decimal("0.00"),
        data=data,
    )

    assert result.is_consistent
    assert result.errors == ()


def test_previous_profit_loss_carryforward_is_zero_when_account_is_missing() -> None:
    service = ProfitAppropriationService()

    report = TrialBalanceReport(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rows=(
            TrialBalanceReportRow(
                account_number="1200",
                opening_debit=Decimal("1000.00"),
                opening_credit=Decimal("0.00"),
                debit_turnover=Decimal("0.00"),
                credit_turnover=Decimal("0.00"),
                closing_debit=Decimal("1000.00"),
                closing_credit=Decimal("0.00"),
            ),
        ),
    )

    result = service.previous_profit_loss_carryforward(
        trial_balance_report=report,
        profit_loss_carryforward_account="2970",
    )

    assert result == Decimal("0.00")
