from decimal import Decimal

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.domain.account_mapping_rule import AccountMappingRule
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.services.closing_result import ClosingResult


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