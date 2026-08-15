"""Tests für EBilanzPreparationService."""

from decimal import Decimal
from unittest.mock import Mock

from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account_type import AccountType
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationService,
)


def test_combines_pre_closing_income_statement_with_closed_balance_sheet(
) -> None:
    """GuV vor Abschluss und Bilanz nach Abschluss werden verbunden."""

    assets = Mock(
        spec=FinancialStatementPosition
    )
    liabilities = Mock(
        spec=FinancialStatementPosition
    )
    income_statement_root = Mock(
        spec=FinancialStatementPosition
    )

    revenue_position = Mock(
        spec=FinancialStatementPosition
    )
    profit_position = Mock(
        spec=FinancialStatementPosition
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={
            revenue_position: Decimal("16500.00"),
        },
    )

    ledger = Ledger()

    ledger.post(
        debit_account="1200",
        credit_account="8020",
        amount=Decimal("5080.00"),
    )

    statement_builder = Mock(
        spec=FinancialStatementBuilder
    )

    statement_builder.build.return_value = {
        profit_position: Decimal("5080.00"),
    }

    service = EBilanzPreparationService(
        statement_builder=statement_builder,
        account_types={
            "1200": AccountType.ASSET,
            "8020": AccountType.EQUITY,
        },
        assets=assets,
        liabilities=liabilities,
    )

    result = service.prepare(
        income_statement=income_statement,
        closed_ledger=ledger,
    )

    assert result.income_statement_amounts == {
        revenue_position: Decimal("16500.00"),
    }

    assert result.balance_sheet_amounts == {
        profit_position: Decimal("5080.00"),
    }

    assert result.amounts == {
        revenue_position: Decimal("16500.00"),
        profit_position: Decimal("5080.00"),
    }

    statement_builder.build.assert_called_once()

    call_kwargs = (
        statement_builder.build.call_args.kwargs
    )

    assert call_kwargs["root_positions"] == (
        assets,
        liabilities,
    )

    balances = call_kwargs["balances"]

    assert {
        balance.account_number
        for balance in balances
    } == {
        "1200",
        "8020",
    }


def test_excludes_income_summary_account_from_balance_sheet(
) -> None:
    """Das technische GuV-Abschlusskonto 8990 wird ausgeschlossen."""

    assets = Mock(
        spec=FinancialStatementPosition
    )
    liabilities = Mock(
        spec=FinancialStatementPosition
    )
    income_statement_root = Mock(
        spec=FinancialStatementPosition
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={},
    )

    ledger = Ledger()

    ledger.post(
        debit_account="1200",
        credit_account="8990",
        amount=Decimal("100.00"),
    )

    statement_builder = Mock(
        spec=FinancialStatementBuilder
    )
    statement_builder.build.return_value = {}

    service = EBilanzPreparationService(
        statement_builder=statement_builder,
        account_types={
            "1200": AccountType.ASSET,
            "8990": AccountType.EQUITY,
        },
        assets=assets,
        liabilities=liabilities,
    )

    service.prepare(
        income_statement=income_statement,
        closed_ledger=ledger,
    )

    balances = (
        statement_builder
        .build
        .call_args
        .kwargs["balances"]
    )

    assert {
        balance.account_number
        for balance in balances
    } == {
        "1200",
    }
