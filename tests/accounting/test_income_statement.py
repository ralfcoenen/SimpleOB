from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement


def test_returns_amount_for_position() -> None:
    revenue = FinancialStatementPosition(
        code="REV",
        name="Umsatzerlöse",
    )

    income_statement = IncomeStatement(
        income_statement=revenue,
        amounts={
            revenue: Decimal("500.00"),
        },
    )

    assert income_statement.amount_for(revenue) == Decimal("500.00")
    
