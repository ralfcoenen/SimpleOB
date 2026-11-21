from decimal import Decimal

import pytest

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.accounting.statement_category import StatementCategory
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.template_account import TemplateAccount
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.closing_result import ClosingResult


def test_sums_multiple_account_balances_for_same_position() -> None:
    bank_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Kassenbestand und Guthaben bei Kreditinstituten",
    )

    first_account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )
    second_account = TemplateAccount(
        account_number="1210",
        name="Weitere Bank",
        account_type=AccountType.ASSET,
    )

    first_rule = AccountMappingRule(
        account_number="1200",
        debit_position=bank_position,
        credit_position=None,
    )
    second_rule = AccountMappingRule(
        account_number="1210",
        debit_position=bank_position,
        credit_position=None,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(first_account, second_account),
        account_mapping_rules=(first_rule, second_rule),
    )

    first_balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1250.00"),
        credit=Decimal("250.00"),
    )
    second_balance = AccountBalance(
        account_number="1210",
        debit=Decimal("700.00"),
        credit=Decimal("200.00"),
    )

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    amounts = builder.build((first_balance, second_balance))

    assert amounts == {
        bank_position: Decimal("1500.00"),
    }


def test_mixed_bank_balances_are_separated_by_side_without_netting() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    provider = HgbFinancialStatementPositionProvider((assets, liabilities))
    bank_asset = provider.get("HGB.266.AKTIVA.B.IV")
    bank_liability = provider.get("HGB.266.PASSIVA.C.2")
    accounts = tuple(
        TemplateAccount(number, name, AccountType.ASSET)
        for number, name in (
            ("198765", "Freies Bankkonto Guthaben"),
            ("187654", "Freies Bankkonto Überziehung"),
            ("176543", "Weiteres Bankkonto Überziehung"),
        )
    )
    chart = ChartOfAccountsTemplate(
        "Mehrere Bankkonten",
        accounts,
        account_mapping_rules=tuple(
            AccountMappingRule(account.account_number, bank_asset, None)
            for account in accounts
        ),
    )
    balances = (
        AccountBalance("198765", debit=Decimal("1200.00")),
        AccountBalance("187654", credit=Decimal("300.00")),
        AccountBalance("176543", debit=Decimal("50.00"), credit=Decimal("250.00")),
    )
    initial_balances = tuple(
        (balance.account_number, balance.debit, balance.credit, balance.balance)
        for balance in balances
    )

    amounts = FinancialStatementBuilder(
        AccountMapper(
            chart,
            bank_account_numbers=frozenset(
                {"198765", "187654", "176543"}
            ),
        )
    ).build(balances, root_positions=(assets, liabilities))

    assert amounts[bank_asset] == Decimal("1200.00")
    assert amounts[bank_liability] == Decimal("500.00")
    assert amounts[assets] == Decimal("1200.00")
    assert amounts[liabilities] == Decimal("500.00")
    assert tuple(
        (balance.account_number, balance.debit, balance.credit, balance.balance)
        for balance in balances
    ) == initial_balances


def test_zero_balance_bank_is_omitted_from_hgb_positions() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    account = TemplateAccount("198765", "Bankkonto", AccountType.ASSET)
    chart = ChartOfAccountsTemplate("Nullsaldo", (account,))

    amounts = FinancialStatementBuilder(
        AccountMapper(chart, bank_account_numbers=frozenset({"198765"}))
    ).build(
        (AccountBalance("198765"),),
        root_positions=(assets, liabilities),
    )

    assert amounts[assets] == Decimal("0.00")
    assert amounts[liabilities] == Decimal("0.00")

def test_aggregates_child_amounts_into_parent_position() -> None:
    cash_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV.1",
        name="Kassenbestand",
    )
    bank_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV.2",
        name="Guthaben bei Kreditinstituten",
    )
    liquid_assets_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Flüssige Mittel",
        children=(
            cash_position,
            bank_position,
        ),
    )

    cash_account = TemplateAccount(
        account_number="1000",
        name="Kasse",
        account_type=AccountType.ASSET,
    )
    bank_account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )

    cash_rule = AccountMappingRule(
        account_number="1000",
        debit_position=cash_position,
        credit_position=None,
    )
    bank_rule = AccountMappingRule(
        account_number="1200",
        debit_position=bank_position,
        credit_position=None,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(
            cash_account,
            bank_account,
        ),
        account_mapping_rules=(
            cash_rule,
            bank_rule,
        ),
    )

    cash_balance = AccountBalance(
        account_number="1000",
        debit=Decimal("250.00"),
    )
    bank_balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1250.00"),
    )

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    amounts = builder.build(
        balances=(cash_balance, bank_balance),
        root_positions=(liquid_assets_position,),
    )

    assert amounts[cash_position] == Decimal("250.00")
    assert amounts[bank_position] == Decimal("1250.00")
    assert amounts[liquid_assets_position] == Decimal("1500.00")


def test_aggregates_equity_positions_to_liabilities() -> None:
    _, liabilities = create_hgb_balance_sheet_structure()

    equity = next(
        position
        for position in liabilities.children
        if position.code == "HGB.266.PASSIVA.A"
    )

    subscribed_capital = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.I"
    )
    capital_reserve = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.II"
    )
    retained_earnings = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.III"
    )
    profit_or_loss_carried_forward = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.IV"
    )
    net_income_or_loss = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.V"
    )

    statutory_reserve = next(
        position
        for position in retained_earnings.children
        if position.code == "HGB.266.PASSIVA.A.III.1"
    )
    controlling_company_reserve = next(
        position
        for position in retained_earnings.children
        if position.code == "HGB.266.PASSIVA.A.III.2"
    )
    articles_reserve = next(
        position
        for position in retained_earnings.children
        if position.code == "HGB.266.PASSIVA.A.III.3"
    )
    other_retained_earnings = next(
        position
        for position in retained_earnings.children
        if position.code == "HGB.266.PASSIVA.A.III.4"
    )

    positions_and_amounts = (
        (subscribed_capital, Decimal("25000.00")),
        (capital_reserve, Decimal("5000.00")),
        (statutory_reserve, Decimal("2000.00")),
        (controlling_company_reserve, Decimal("1500.00")),
        (articles_reserve, Decimal("3000.00")),
        (other_retained_earnings, Decimal("4500.00")),
        (profit_or_loss_carried_forward, Decimal("4000.00")),
        (net_income_or_loss, Decimal("10000.00")),
    )

    accounts = tuple(
        TemplateAccount(
            account_number=str(2000 + index),
            name=position.name,
            account_type=AccountType.EQUITY,
        )
        for index, (position, _) in enumerate(
            positions_and_amounts,
            start=1,
        )
    )

    rules = tuple(
        AccountMappingRule(
            account_number=account.account_number,
            debit_position=None,
            credit_position=position,
        )
        for account, (position, _) in zip(
            accounts,
            positions_and_amounts,
            strict=True,
        )
    )

    balances = tuple(
        AccountBalance(
            account_number=account.account_number,
            credit=amount,
        )
        for account, (_, amount) in zip(
            accounts,
            positions_and_amounts,
            strict=True,
        )
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Eigenkapital-Testkontenrahmen",
        accounts=accounts,
        account_mapping_rules=rules,
    )

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    amounts = builder.build(
        balances=balances,
        root_positions=(liabilities,),
    )

    assert amounts[subscribed_capital] == Decimal("25000.00")
    assert amounts[capital_reserve] == Decimal("5000.00")

    assert amounts[statutory_reserve] == Decimal("2000.00")
    assert amounts[controlling_company_reserve] == Decimal("1500.00")
    assert amounts[articles_reserve] == Decimal("3000.00")
    assert amounts[other_retained_earnings] == Decimal("4500.00")

    assert amounts[retained_earnings] == Decimal("11000.00")
    assert amounts[profit_or_loss_carried_forward] == Decimal("4000.00")
    assert amounts[net_income_or_loss] == Decimal("10000.00")

    assert amounts[equity] == Decimal("55000.00")
    assert amounts[liabilities] == Decimal("55000.00")


@pytest.mark.parametrize(
    ("loss_account_number", "loss_account_name"),
    (
        ("8021", "Jahresfehlbetrag"),
        ("9503", "SimpleOB – Jahresfehlbetrag"),
    ),
)
def test_direct_hgb_balance_sheet_balances_with_booked_loss_account(
    loss_account_number: str,
    loss_account_name: str,
) -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    provider = HgbFinancialStatementPositionProvider(
        (assets, liabilities, income_statement)
    )
    bank_position = provider.get("HGB.266.AKTIVA.B.IV")
    capital_position = provider.get("HGB.266.PASSIVA.A.I")
    loss_position = provider.get("HGB.266.PASSIVA.A.V")
    chart = ChartOfAccountsTemplate(
        name="Jahresfehlbetrag-Test",
        accounts=(
            TemplateAccount("1800", "Bank", AccountType.ASSET),
            TemplateAccount(
                "2900",
                "Gezeichnetes Kapital",
                AccountType.EQUITY,
            ),
            TemplateAccount(
                loss_account_number,
                loss_account_name,
                AccountType.EQUITY,
            ),
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1800",
                debit_position=bank_position,
                credit_position=None,
            ),
            AccountMappingRule(
                account_number="2900",
                debit_position=None,
                credit_position=capital_position,
            ),
            AccountMappingRule(
                account_number=loss_account_number,
                debit_position=loss_position,
                credit_position=None,
            ),
        ),
    )
    balances = (
        AccountBalance("1800", debit=Decimal("4000.00")),
        AccountBalance("2900", credit=Decimal("5000.00")),
        AccountBalance(loss_account_number, debit=Decimal("1000.00")),
    )

    amounts = FinancialStatementBuilder(AccountMapper(chart)).build(
        balances=balances,
        root_positions=(assets, liabilities),
    )
    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=amounts,
    )

    assert amounts[loss_position] == Decimal("-1000.00")
    assert balance_sheet.amount_for(assets) == Decimal("4000.00")
    assert balance_sheet.amount_for(liabilities) == Decimal("4000.00")
    assert balance_sheet.is_balanced()


def test_build_includes_closing_result_in_result_position() -> None:
    net_income_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.V",
        name="Jahresüberschuss/Jahresfehlbetrag",
        category=StatementCategory.RESULT,
    )

    liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA",
        name="Passiva",
        children=(net_income_position,),
    )

    builder = FinancialStatementBuilder(mapper=...)

    amounts = builder.build(
        balances=(),
        root_positions=(liabilities,),
        closing_result=ClosingResult(
            net_income=Decimal("300.00"),
        ),
        result_position=net_income_position,
    )

    assert amounts[net_income_position] == Decimal("300.00")
    assert amounts[liabilities] == Decimal("300.00")

def test_maps_income_statement_counter_balances_as_negative() -> None:
    expense_position = FinancialStatementPosition(
        code="HGB.275.GKV.8",
        name="Sonstige betriebliche Aufwendungen",
    )
    revenue_position = FinancialStatementPosition(
        code="HGB.275.GKV.1",
        name="Umsatzerlöse",
    )

    expense_account = TemplateAccount(
        account_number="4930",
        name="Bürobedarf",
        account_type=AccountType.EXPENSE,
    )
    revenue_account = TemplateAccount(
        account_number="8400",
        name="Erlöse",
        account_type=AccountType.REVENUE,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="GuV-Gegensalden",
        accounts=(
            expense_account,
            revenue_account,
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="4930",
                debit_position=expense_position,
                credit_position=None,
            ),
            AccountMappingRule(
                account_number="8400",
                debit_position=None,
                credit_position=revenue_position,
            ),
        ),
    )

    balances = (
        AccountBalance(
            account_number="4930",
            credit=Decimal("250.00"),
        ),
        AccountBalance(
            account_number="8400",
            debit=Decimal("400.00"),
        ),
    )

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    amounts = builder.build(
        balances=balances
    )

    assert amounts[expense_position] == Decimal("-250.00")
    assert amounts[revenue_position] == Decimal("-400.00")
