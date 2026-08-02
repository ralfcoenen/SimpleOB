from decimal import Decimal

from openbilanz.accounting.account_balance import AccountBalance
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


def test_maps_debit_balance_to_debit_position() -> None:
    bank_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Kassenbestand und Guthaben bei Kreditinstituten",
    )

    account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )

    rule = AccountMappingRule(
        account_number="1200",
        debit_position=bank_position,
        credit_position=None,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(account,),
        account_mapping_rules=(rule,),
    )

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1250.00"),
        credit=Decimal("250.00"),
    )

    mapper = AccountMapper(chart_of_accounts)

    assert mapper.position_for(balance) is bank_position



from decimal import Decimal

def test_maps_credit_balance_to_credit_position() -> None:
    credit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.2",
        name="Verbindlichkeiten gegenüber Kreditinstituten",
    )

    account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )

    rule = AccountMappingRule(
        account_number="1200",
        debit_position=None,
        credit_position=credit_position,
    )

    chart = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(account,),
        account_mapping_rules=(rule,),
    )

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("250.00"),
        credit=Decimal("1250.00"),
    )

    mapper = AccountMapper(chart)

    assert mapper.position_for(balance) is credit_position
    
    