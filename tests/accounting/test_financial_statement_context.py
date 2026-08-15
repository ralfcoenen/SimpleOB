"""Tests für den gemeinsamen Abschlusskontext."""

from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.financial_statement_context import (
    FinancialStatementContext,
    create_standard_financial_statement_context,
)
from openbilanz.accounting.mapper import AccountMapper


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
