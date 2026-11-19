from decimal import Decimal

import pytest

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_builder import FinancialStatementBuilder
from simpleob.accounting.financial_statement_position import FinancialStatementPosition
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.errors import UnsupportedPersonAccountBalanceError
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount


def _chart() -> tuple[ChartOfAccountsTemplate, FinancialStatementPosition]:
    position = FinancialStatementPosition(code="HGB.TEST.ASSET", name="Forderungen")
    account = TemplateAccount("10000", "Debitor", AccountType.ASSET)
    mapped = TemplateAccount("1200", "Bank", AccountType.ASSET)
    return (
        ChartOfAccountsTemplate(
            "Test",
            (account, mapped),
            (AccountMappingRule("1200", debit_position=position, credit_position=None),),
            (("10000", PersonAccountRole.DEBITOR),),
        ),
        position,
    )


def test_nonzero_person_saldo_is_identified_and_blocks_hgb_mapping():
    chart, _position = _chart()
    mapper = AccountMapper(chart)
    balance = AccountBalance("10000", debit=Decimal("12.00"))
    assert chart.is_person_account("10000")
    with pytest.raises(UnsupportedPersonAccountBalanceError, match="Personenkonto 10000"):
        mapper.position_for(balance)
    with pytest.raises(UnsupportedPersonAccountBalanceError, match="noch nicht unterstützt"):
        FinancialStatementBuilder(mapper).build((balance,))


def test_zero_person_saldo_does_not_block_and_regular_mapping_is_unchanged():
    chart, position = _chart()
    mapper = AccountMapper(chart)
    builder = FinancialStatementBuilder(mapper)
    assert builder.build((AccountBalance("10000"),)) == {}
    mapped = builder.build((AccountBalance("1200", debit=Decimal("4.00")),))
    assert mapped[position] == Decimal("4.00")
