from decimal import Decimal

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.domain.account_mapping_rule import AccountMappingRule
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.template_account import TemplateAccount


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
        
    