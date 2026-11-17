from decimal import Decimal

import pytest

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
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
from simpleob.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from simpleob.hgb.balance_sheet_structure import (
    NON_COVERED_EQUITY_DEFICIT_CODE,
    NON_COVERED_EQUITY_OFFSET_CODE,
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.profit_appropriation_presentation_service import (
    ProfitAppropriationPresentationService,
)
from simpleob.services.uncovered_equity_deficit_presentation_service import (
    UncoveredEquityDeficitPresentationService,
)


def _find(
    root: FinancialStatementPosition,
    code: str,
) -> FinancialStatementPosition:
    if root.code == code:
        return root
    for child in root.children:
        try:
            return _find(child, code)
        except AssertionError:
            continue
    raise AssertionError(f"Position {code} not found")


def _balance_with_equity(equity_amount: Decimal) -> BalanceSheet:
    assets, liabilities = create_hgb_balance_sheet_structure()
    cash = _find(assets, "HGB.266.AKTIVA.B.IV")
    equity = _find(liabilities, "HGB.266.PASSIVA.A")
    capital = _find(liabilities, "HGB.266.PASSIVA.A.I")
    carryforward = _find(liabilities, "HGB.266.PASSIVA.A.IV")
    payables = _find(liabilities, "HGB.266.PASSIVA.C.4")
    capital_amount = Decimal("1000.00")
    carryforward_amount = equity_amount - capital_amount
    payable_amount = Decimal("2000.00") - equity_amount
    return BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("2000.00"),
            cash: Decimal("2000.00"),
            liabilities: Decimal("2000.00"),
            equity: equity_amount,
            capital: capital_amount,
            carryforward: carryforward_amount,
            payables: payable_amount,
        },
    )


def test_negative_equity_case_is_presented_without_changing_raw_positions() -> None:
    raw = _balance_with_equity(Decimal("-5000.00"))
    original_amounts = dict(raw.amounts)
    equity = _find(raw.liabilities, "HGB.266.PASSIVA.A")
    capital = _find(raw.liabilities, "HGB.266.PASSIVA.A.I")
    carryforward = _find(raw.liabilities, "HGB.266.PASSIVA.A.IV")
    payables = _find(raw.liabilities, "HGB.266.PASSIVA.C.4")

    presented = UncoveredEquityDeficitPresentationService.apply(raw)
    deficit = _find(presented.assets, NON_COVERED_EQUITY_DEFICIT_CODE)
    offset = _find(presented.liabilities, NON_COVERED_EQUITY_OFFSET_CODE)

    assert raw.amount_for(equity) == Decimal("-5000.00")
    assert raw.amount_for(capital) == Decimal("1000.00")
    assert raw.amount_for(carryforward) == Decimal("-6000.00")
    assert raw.amount_for(presented.assets) == Decimal("2000.00")
    assert presented.amount_for(deficit) == Decimal("5000.00")
    assert presented.amount_for(capital) == Decimal("1000.00")
    assert presented.amount_for(carryforward) == Decimal("-6000.00")
    assert presented.amount_for(offset) == Decimal("5000.00")
    assert presented.amount_for(equity) == Decimal("0.00")
    assert presented.amount_for(payables) == Decimal("7000.00")
    assert presented.amount_for(presented.assets) == Decimal("7000.00")
    assert presented.amount_for(presented.liabilities) == Decimal("7000.00")
    assert raw.amounts == original_amounts
    assert raw.is_balanced()
    assert presented.is_balanced()


@pytest.mark.parametrize("equity", (Decimal("100.00"), Decimal("0.00")))
def test_nonnegative_equity_has_no_deficit(equity: Decimal) -> None:
    raw = _balance_with_equity(equity)

    presented = UncoveredEquityDeficitPresentationService.apply(raw)

    assert presented is raw
    assert presented.amount_for(presented.assets) == Decimal("2000.00")
    assert presented.is_balanced()


@pytest.mark.parametrize(
    ("equity", "expected_deficit"),
    (
        (Decimal("-2000.00"), Decimal("2000.00")),
        (Decimal("0.00"), Decimal("0.00")),
        (Decimal("500.00"), Decimal("0.00")),
    ),
)
def test_profit_reduces_or_eliminates_deficit(
    equity: Decimal,
    expected_deficit: Decimal,
) -> None:
    raw = _balance_with_equity(equity)

    presented = UncoveredEquityDeficitPresentationService.apply(raw)
    deficit_position = _find(
        presented.assets,
        NON_COVERED_EQUITY_DEFICIT_CODE,
    )

    assert presented.amount_for(deficit_position) == expected_deficit
    assert presented.is_balanced()


def test_application_is_idempotent() -> None:
    raw = _balance_with_equity(Decimal("-5000.00"))

    first = UncoveredEquityDeficitPresentationService.apply(raw)
    second = UncoveredEquityDeficitPresentationService.apply(first)

    assert second is first
    assert second.amounts == first.amounts


def test_deficit_uses_balance_after_profit_appropriation() -> None:
    raw = _balance_with_equity(Decimal("-5000.00"))
    liabilities = raw.liabilities
    statutory = _find(liabilities, "HGB.266.PASSIVA.A.III.1")
    other_reserves = _find(liabilities, "HGB.266.PASSIVA.A.III.4")
    carryforward = _find(liabilities, "HGB.266.PASSIVA.A.IV")
    payables = _find(liabilities, "HGB.266.PASSIVA.C.4")
    numbers = {
        "2930": statutory,
        "2960": other_reserves,
        "2970": carryforward,
        "3500": payables,
    }
    chart = ChartOfAccountsTemplate(
        "Test",
        tuple(
            TemplateAccount(
                number,
                number,
                AccountType.LIABILITY
                if number == "3500"
                else AccountType.EQUITY,
            )
            for number in numbers
        ),
        account_mapping_rules=tuple(
            AccountMappingRule(number, None, position)
            for number, position in numbers.items()
        ),
    )
    control_accounts = AccountingControlAccounts(
        opening_balance_account="9000",
        income_summary_account="8990",
        profit_account="9502",
        loss_account="9503",
        profit_loss_carryforward_account="2970",
        statutory_reserve_account="2930",
        other_revenue_reserves_account="2960",
        distribution_liability_account="3500",
        depreciation_expense_account="6220",
        fixed_asset_disposal_gain_account="4830",
        fixed_asset_disposal_loss_account="6300",
    )
    appropriation_data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("0.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("0.00"),
    )

    after_appropriation = ProfitAppropriationPresentationService.apply(
        balance_sheet=raw,
        data=appropriation_data,
        net_income=Decimal("-6000.00"),
        previous_carryforward=Decimal("0.00"),
        chart_of_accounts=chart,
        control_accounts=control_accounts,
    )
    displayed = UncoveredEquityDeficitPresentationService.apply(
        after_appropriation
    )

    displayed_equity = _find(displayed.liabilities, "HGB.266.PASSIVA.A")
    deficit = _find(displayed.assets, NON_COVERED_EQUITY_DEFICIT_CODE)
    assert after_appropriation.amount_for(displayed_equity) == (
        Decimal("-5000.00")
    )
    assert displayed.amount_for(displayed_equity) == Decimal("0.00")
    assert displayed.amount_for(deficit) == Decimal("5000.00")
    assert displayed.is_balanced()


def test_unbalanced_raw_balance_sheet_is_rejected() -> None:
    raw = _balance_with_equity(Decimal("-5000.00"))
    amounts = dict(raw.amounts)
    amounts[raw.assets] = Decimal("1900.00")
    unbalanced = BalanceSheet(
        assets=raw.assets,
        liabilities=raw.liabilities,
        amounts=amounts,
    )

    with pytest.raises(ValueError, match="ausgeglichenen Rohbilanz"):
        UncoveredEquityDeficitPresentationService.apply(unbalanced)


def test_ledger_balances_and_ebilanz_values_remain_raw() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    cash = _find(assets, "HGB.266.AKTIVA.B.IV")
    capital = _find(liabilities, "HGB.266.PASSIVA.A.I")
    carryforward = _find(liabilities, "HGB.266.PASSIVA.A.IV")
    payables = _find(liabilities, "HGB.266.PASSIVA.C.4")
    accounts = (
        TemplateAccount("1800", "Bank", AccountType.ASSET),
        TemplateAccount("2970", "Vortrag", AccountType.EQUITY),
        TemplateAccount("2900", "Kapital", AccountType.EQUITY),
        TemplateAccount("3300", "Verbindlichkeit", AccountType.LIABILITY),
    )
    chart = ChartOfAccountsTemplate(
        "Test",
        accounts,
        account_mapping_rules=(
            AccountMappingRule(
                "1800",
                cash,
                None,
            ),
            AccountMappingRule(
                "2970",
                carryforward,
                carryforward,
            ),
            AccountMappingRule("2900", None, capital),
            AccountMappingRule("3300", None, payables),
        ),
    )
    ledger = Ledger()
    ledger.post(
        debit_account="1800",
        credit_account="9000",
        amount=Decimal("2000.00"),
    )
    ledger.post(
        debit_account="2970",
        credit_account="9000",
        amount=Decimal("6000.00"),
    )
    ledger.post(
        debit_account="9000",
        credit_account="2900",
        amount=Decimal("1000.00"),
    )
    ledger.post(
        debit_account="9000",
        credit_account="3300",
        amount=Decimal("7000.00"),
    )
    raw_balances = tuple(
        balance
        for balance in ledger.balances()
        if balance.account_number != "9000"
    )
    builder = FinancialStatementBuilder(AccountMapper(chart))
    raw = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=builder.build(
            balances=raw_balances,
            root_positions=(assets, liabilities),
        ),
    )
    ledger_before = tuple(
        (balance.account_number, balance.debit, balance.credit)
        for balance in ledger.balances()
    )
    income_statement = create_hgb_income_statement_structure()
    facts_before = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=raw,
        income_statement=income_statement,
    )

    displayed = UncoveredEquityDeficitPresentationService.apply(raw)
    facts_after = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=raw,
        income_statement=income_statement,
    )
    ledger_after = tuple(
        (balance.account_number, balance.debit, balance.credit)
        for balance in ledger.balances()
    )
    opening_balance_account = ledger.get_account("9000")

    assert displayed is not raw
    assert ledger_after == ledger_before
    assert opening_balance_account.debit == opening_balance_account.credit
    assert facts_after == facts_before
    assert raw.amount_for(_find(raw.liabilities, "HGB.266.PASSIVA.A")) == (
        Decimal("-5000.00")
    )
