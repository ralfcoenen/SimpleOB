"""Tests für Buchungsvorschläge zur Ergebnisverwendung."""

from datetime import date
from decimal import Decimal

from simpleob.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)
from simpleob.services.profit_appropriation_posting_service import (
    ProfitAppropriationPostingService,
)


def _control_accounts() -> AccountingControlAccounts:
    return AccountingControlAccounts(
        opening_balance_account="9000",
        income_summary_account="8020",
        profit_account="8020",
        loss_account="8021",
        profit_loss_carryforward_account="2970",
        statutory_reserve_account="0846",
        other_revenue_reserves_account="0855",
        distribution_liability_account="0755",
        depreciation_expense_account="4830",
        fixed_asset_disposal_gain_account="4900",
        fixed_asset_disposal_loss_account="8500",
    )


def test_build_proposals_creates_expected_postings() -> None:
    service = ProfitAppropriationPostingService()

    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("1000.00"),
        other_revenue_reserves_addition=Decimal("2000.00"),
        statutory_reserve_release=Decimal("300.00"),
        other_revenue_reserves_release=Decimal("400.00"),
        distribution=Decimal("5000.00"),
        profit_loss_carryforward=Decimal("6307.01"),
    )

    proposals = service.build_proposals(
        data=data,
        booking_date=date(2027, 3, 15),
        control_accounts=_control_accounts(),
    )

    assert len(proposals) == 5

    by_type = {
        proposal.posting_type: proposal
        for proposal in proposals
    }

    statutory_addition = by_type[
        ProfitAppropriationPostingType.STATUTORY_RESERVE_ADDITION
    ]
    assert statutory_addition.amount == Decimal("1000.00")
    assert statutory_addition.debit_account_number == "2970"
    assert statutory_addition.credit_account_number == "0846"

    other_addition = by_type[
        ProfitAppropriationPostingType.OTHER_REVENUE_RESERVES_ADDITION
    ]
    assert other_addition.amount == Decimal("2000.00")
    assert other_addition.debit_account_number == "2970"
    assert other_addition.credit_account_number == "0855"

    statutory_release = by_type[
        ProfitAppropriationPostingType.STATUTORY_RESERVE_RELEASE
    ]
    assert statutory_release.amount == Decimal("300.00")
    assert statutory_release.debit_account_number == "0846"
    assert statutory_release.credit_account_number == "2970"

    other_release = by_type[
        ProfitAppropriationPostingType.OTHER_REVENUE_RESERVES_RELEASE
    ]
    assert other_release.amount == Decimal("400.00")
    assert other_release.debit_account_number == "0855"
    assert other_release.credit_account_number == "2970"

    distribution = by_type[
        ProfitAppropriationPostingType.DISTRIBUTION
    ]
    assert distribution.amount == Decimal("5000.00")
    assert distribution.debit_account_number == "2970"
    assert distribution.credit_account_number == "0755"

    assert all(
        proposal.booking_date == date(2027, 3, 15)
        for proposal in proposals
    )


def test_build_proposals_omits_zero_amounts_and_carryforward() -> None:
    service = ProfitAppropriationPostingService()

    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("1000.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("14007.01"),
    )

    proposals = service.build_proposals(
        data=data,
        booking_date=date(2027, 3, 15),
        control_accounts=_control_accounts(),
    )

    assert len(proposals) == 1
    assert (
        proposals[0].posting_type
        is ProfitAppropriationPostingType.STATUTORY_RESERVE_ADDITION
    )
    assert proposals[0].amount == Decimal("1000.00")
