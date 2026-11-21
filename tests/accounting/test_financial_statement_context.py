"""Tests für den gemeinsamen Abschlusskontext."""

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.financial_statement_context import (
    FinancialStatementContext,
    create_financial_statement_context,
    create_standard_financial_statement_context,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.accounting_account_roles import AccountingAccountRoles


def test_creates_standard_financial_statement_context(
) -> None:
    context = (
        create_standard_financial_statement_context()
    )

    assert isinstance(
        context,
        FinancialStatementContext,
    )

    assert isinstance(
        context.account_mapper,
        AccountMapper,
    )

    assert isinstance(
        context.statement_builder,
        FinancialStatementBuilder,
    )

    assert context.chart_of_accounts.accounts

    assert len(context.accounts) == len(
        context.chart_of_accounts.accounts
    )

    assert context.account_types == {
        account.account_number:
            account.account_type
        for account
        in context.chart_of_accounts.accounts
    }


def test_maps_vat_current_year_account_by_balance_side():
    context = create_standard_financial_statement_context()

    debit_position, debit_amount = context.account_mapper.map_balance(
        AccountBalance("3840", debit=12, credit=0)
    )
    credit_position, credit_amount = context.account_mapper.map_balance(
        AccountBalance("3840", debit=0, credit=19)
    )

    assert debit_position.code == "HGB.266.AKTIVA.B.II.4"
    assert debit_amount == 12
    assert credit_position.code == "HGB.266.PASSIVA.C.8"
    assert credit_amount == 19


def test_financial_context_passes_configured_bank_roles_to_mapper():
    standard = create_standard_financial_statement_context()
    context = create_financial_statement_context(
        assets=standard.assets,
        liabilities=standard.liabilities,
        income_statement=standard.income_statement,
        chart_of_accounts=standard.chart_of_accounts,
        accounts=standard.accounts,
        account_roles=AccountingAccountRoles(
            cash_accounts=frozenset(),
            bank_accounts=frozenset({"1200"}),
            general_rate_sales_accounts=frozenset(),
        ),
    )

    position, amount = context.account_mapper.map_balance(
        AccountBalance("1200", credit=250)
    )

    assert position.code == "HGB.266.PASSIVA.C.2"
    assert amount == 250
