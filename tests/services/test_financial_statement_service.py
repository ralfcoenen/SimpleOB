"""Tests für die gemeinsame Bilanz- und GuV-Erzeugung."""
from decimal import Decimal

from openbilanz.accounting.financial_statement_context import (
    create_standard_financial_statement_context,
)
from openbilanz.accounting.ledger import Ledger
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.financial_statement_service import (
    FinancialStatementService,
)


def _post(
    ledger: Ledger,
    *,
    debit_account: str,
    credit_account: str,
    amount: str,
) -> None:
    ledger.post(
        debit_account,
        credit_account,
        Decimal(amount),
    )

def test_build_uses_current_ledger_for_open_fiscal_year() -> None:
    context = create_standard_financial_statement_context()

    ledger = Ledger()
    pre_closing_ledger = Ledger()

    _post(
        ledger,
        debit_account="1200",
        credit_account="8400",
        amount="1190.00",
    )

    service = FinancialStatementService(
        closing_service=ClosingService(),
    )

    result = service.build(
        ledger=ledger,
        pre_closing_ledger=pre_closing_ledger,
        is_closed=False,
        context=context,
    )

    assert result.net_income == Decimal("1190.00")


def test_build_uses_pre_closing_ledger_for_closed_fiscal_year() -> None:
    context = create_standard_financial_statement_context()

    ledger = Ledger()
    pre_closing_ledger = Ledger()

    _post(
        pre_closing_ledger,
        debit_account="1200",
        credit_account="8400",
        amount="1190.00",
    )

    service = FinancialStatementService(
        closing_service=ClosingService(),
    )

    result = service.build(
        ledger=ledger,
        pre_closing_ledger=pre_closing_ledger,
        is_closed=True,
        context=context,
    )

    assert result.net_income == Decimal("1190.00")


def test_build_includes_result_in_balance_sheet() -> None:
    context = create_standard_financial_statement_context()

    ledger = Ledger()
    pre_closing_ledger = Ledger()

    _post(
        ledger,
        debit_account="1200",
        credit_account="8400",
        amount="1190.00",
    )

    service = FinancialStatementService(
        closing_service=ClosingService(),
    )

    result = service.build(
        ledger=ledger,
        pre_closing_ledger=pre_closing_ledger,
        is_closed=False,
        context=context,
    )

    equity = next(
        position
        for position in context.liabilities.children
        if position.code == "HGB.266.PASSIVA.A"
    )

    result_position = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.V"
    )
    assert result.balance_sheet is not None
    assert (
        result.balance_sheet.amount_for(result_position)
        == Decimal("1190.00")
    )
