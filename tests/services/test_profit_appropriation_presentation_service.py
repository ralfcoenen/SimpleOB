"""Regressionstests für Variante B der Bilanzdarstellung."""

from decimal import Decimal

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.domain.template_account import TemplateAccount
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.services.profit_appropriation_presentation_service import (
    ProfitAppropriationPresentationService,
)


def _find(root: FinancialStatementPosition, code: str):
    if root.code == code:
        return root
    for child in root.children:
        found = _find(child, code)
        if found is not None:
            return found
    return None


def _chart() -> tuple[ChartOfAccountsTemplate, AccountingControlAccounts]:
    assets, liabilities = create_hgb_balance_sheet_structure()
    positions = {
        code: _find(liabilities, code)
        for code in (
            "HGB.266.PASSIVA.A.III.1",
            "HGB.266.PASSIVA.A.III.4",
            "HGB.266.PASSIVA.A.IV",
            "HGB.266.PASSIVA.C.4",
        )
    }
    numbers = {
        "2930": "HGB.266.PASSIVA.A.III.1",
        "2960": "HGB.266.PASSIVA.A.III.4",
        "2970": "HGB.266.PASSIVA.A.IV",
        "3500": "HGB.266.PASSIVA.C.4",
    }
    chart = ChartOfAccountsTemplate(
        name="Test",
        accounts=tuple(
            TemplateAccount(
                account_number=number,
                name=number,
                account_type=(
                    AccountType.LIABILITY
                    if number == "3500"
                    else AccountType.EQUITY
                ),
            )
            for number in numbers
        ),
        account_mapping_rules=tuple(
            AccountMappingRule(
                account_number=number,
                debit_position=None,
                credit_position=positions[code],
            )
            for number, code in numbers.items()
        ),
    )
    controls = AccountingControlAccounts(
        opening_balance_account="9000",
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
        profit_loss_carryforward_account="2970",
        statutory_reserve_account="2930",
        other_revenue_reserves_account="2960",
        distribution_liability_account="3500",
        depreciation_expense_account="6200",
        fixed_asset_disposal_gain_account="8820",
        fixed_asset_disposal_loss_account="6890",
    )
    return chart, controls


def test_variant_b_example_preserves_profit_and_balance_sheet() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    cash = _find(assets, "HGB.266.AKTIVA.B.IV")
    statutory = _find(liabilities, "HGB.266.PASSIVA.A.III.1")
    capital = _find(liabilities, "HGB.266.PASSIVA.A.I")
    carry = _find(liabilities, "HGB.266.PASSIVA.A.IV")
    result = _find(liabilities, "HGB.266.PASSIVA.A.V")
    assert (
        statutory is not None
        and capital is not None
        and carry is not None
        and result is not None
        and cash is not None
    )
    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("17500.00"),
            cash: Decimal("17500.00"),
            liabilities: Decimal("17500.00"),
            capital: Decimal("10000.00"),
            statutory: Decimal("1500.00"),
            carry: Decimal("-4000.00"),
            result: Decimal("10000.00"),
        },
    )
    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("1500.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("0.00"),
    )
    chart, controls = _chart()

    presented = ProfitAppropriationPresentationService.apply(
        balance_sheet=balance_sheet,
        data=data,
        net_income=Decimal("10000.00"),
        previous_carryforward=Decimal("-4000.00"),
        chart_of_accounts=chart,
        control_accounts=controls,
    )
    presented_reserve = _find(
        presented.liabilities,
        "HGB.266.PASSIVA.A.III.1",
    )
    presented_carry = _find(
        presented.liabilities,
        "HGB.266.PASSIVA.A.IV",
    )
    presented_result = _find(
        presented.liabilities,
        "HGB.266.PASSIVA.A.V",
    )
    assert presented_reserve and presented_carry and presented_result
    assert presented.amount_for(presented_reserve) == Decimal("3000.00")
    assert presented.amount_for(presented_carry) == Decimal("0.00")
    assert presented.amount_for(presented_result) == Decimal("4500.00")
    assert presented.amount_for(presented.liabilities) == Decimal("17500.00")
    assert presented.is_balanced()


def test_balance_profit_loss_formula_keeps_new_carryforward_distinct() -> None:
    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("1500.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("0.00"),
    )
    assert (
        ProfitAppropriationPresentationService.remaining_balance_profit_loss(
            net_income=Decimal("10000.00"),
            previous_carryforward=Decimal("-4000.00"),
            data=data,
        )
        == Decimal("4500.00")
    )


def test_distribution_creates_presentation_liability_without_booking() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    cash = _find(assets, "HGB.266.AKTIVA.B.IV")
    capital = _find(liabilities, "HGB.266.PASSIVA.A.I")
    result = _find(liabilities, "HGB.266.PASSIVA.A.V")
    payable = _find(liabilities, "HGB.266.PASSIVA.C.4")
    assert cash and capital and result and payable
    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("1000.00"),
            cash: Decimal("1000.00"),
            liabilities: Decimal("1000.00"),
            capital: Decimal("500.00"),
            result: Decimal("500.00"),
        },
    )
    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("0.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("100.00"),
        profit_loss_carryforward=Decimal("0.00"),
    )
    chart, controls = _chart()

    presented = ProfitAppropriationPresentationService.apply(
        balance_sheet=balance_sheet,
        data=data,
        net_income=Decimal("500.00"),
        previous_carryforward=Decimal("0.00"),
        chart_of_accounts=chart,
        control_accounts=controls,
    )

    presented_payable = _find(
        presented.liabilities,
        "HGB.266.PASSIVA.C.4",
    )
    assert presented_payable is not None
    assert presented.amount_for(presented_payable) == Decimal("100.00")
    assert presented.is_balanced()
