from decimal import Decimal

import pytest

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.template_account import TemplateAccount


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

    position, amount = mapper.map_balance(balance)

    assert position is bank_position
    assert amount == Decimal("1000.00")


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

    position, amount = mapper.map_balance(balance)

    assert position is credit_position
    assert amount == Decimal("1000.00")


def test_maps_debit_balance_of_liability_to_explicit_debit_position() -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.8",
        name="Sonstige Verbindlichkeiten",
    )
    account = TemplateAccount(
        account_number="3300",
        name="Lieferantenverbindlichkeiten",
        account_type=AccountType.LIABILITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Verbindlichkeits-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="3300",
                debit_position=debit_position,
                credit_position=None,
            ),
        ),
    )

    position, amount = AccountMapper(chart).map_balance(
        AccountBalance(
            account_number="3300",
            debit=Decimal("1000.00"),
        )
    )

    assert position is debit_position
    assert amount == Decimal("1000.00")


@pytest.mark.parametrize(
    ("account_number", "position_code"),
    (
        ("8021", "HGB.266.PASSIVA.A.V"),
        ("9503", "HGB.266.PASSIVA.A.V"),
        ("2978", "HGB.266.PASSIVA.A.IV"),
        ("7720", "HGB.266.PASSIVA.A.IV"),
    ),
)
def test_maps_debit_balance_of_equity_to_debit_position_as_negative(
    account_number: str,
    position_code: str,
) -> None:
    position = FinancialStatementPosition(
        code=position_code,
        name="Eigenkapitalposition",
    )
    account = TemplateAccount(
        account_number=account_number,
        name="Eigenkapitalkonto",
        account_type=AccountType.EQUITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Eigenkapital-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number=account_number,
                debit_position=position,
                credit_position=None,
            ),
        ),
    )

    mapped_position, amount = AccountMapper(chart).map_balance(
        AccountBalance(
            account_number=account_number,
            debit=Decimal("1000.00"),
        )
    )

    assert mapped_position is position
    assert amount == Decimal("-1000.00")


@pytest.mark.parametrize(
    ("account_number", "position_code"),
    (
        ("8020", "HGB.266.PASSIVA.A.V"),
        ("9502", "HGB.266.PASSIVA.A.V"),
        ("2970", "HGB.266.PASSIVA.A.IV"),
    ),
)
def test_maps_credit_balance_of_equity_to_credit_position_as_positive(
    account_number: str,
    position_code: str,
) -> None:
    position = FinancialStatementPosition(
        code=position_code,
        name="Eigenkapitalposition",
    )
    account = TemplateAccount(
        account_number=account_number,
        name="Eigenkapitalkonto",
        account_type=AccountType.EQUITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Eigenkapital-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number=account_number,
                debit_position=None,
                credit_position=position,
            ),
        ),
    )

    mapped_position, amount = AccountMapper(chart).map_balance(
        AccountBalance(
            account_number=account_number,
            credit=Decimal("1000.00"),
        )
    )

    assert mapped_position is position
    assert amount == Decimal("1000.00")


def test_equity_credit_balance_without_credit_position_still_fails() -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.V",
        name="Jahresfehlbetrag",
    )
    account = TemplateAccount(
        account_number="9503",
        name="Jahresfehlbetrag",
        account_type=AccountType.EQUITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Eigenkapital-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="9503",
                debit_position=debit_position,
                credit_position=None,
            ),
        ),
    )

    with pytest.raises(ValueError, match="no credit position defined"):
        AccountMapper(chart).map_balance(
            AccountBalance(
                account_number="9503",
                credit=Decimal("1000.00"),
            )
        )


def test_maps_equity_debit_balance_to_credit_position_as_negative() -> None:
    carryforward_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.IV",
        name="Gewinnvortrag/Verlustvortrag",
    )

    account = TemplateAccount(
        account_number="2970",
        name="Gewinnvortrag / Verlustvortrag",
        account_type=AccountType.EQUITY,
    )

    rule = AccountMappingRule(
        account_number="2970",
        debit_position=None,
        credit_position=carryforward_position,
    )

    chart = ChartOfAccountsTemplate(
        name="SimpleOB",
        accounts=(account,),
        account_mapping_rules=(rule,),
    )

    balance = AccountBalance(
        account_number="2970",
        debit=Decimal("3941.64"),
        credit=Decimal("0.00"),
    )

    mapper = AccountMapper(chart)

    position, amount = mapper.map_balance(balance)

    assert position is carryforward_position
    assert amount == Decimal("-3941.64")
