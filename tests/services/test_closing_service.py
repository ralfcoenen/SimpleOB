from decimal import Decimal

from openbilanz.services.closing_service import ClosingService

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement

from openbilanz.services.closing_result import ClosingResult
from openbilanz.accounting.statement_category import StatementCategory


def test_calculates_net_income_from_income_and_expenses() -> None:
    service = ClosingService()

    net_income = service.calculate_net_income(
        income=Decimal("500.00"),
        expenses=Decimal("200.00"),
    )

    assert net_income == Decimal("300.00")
    
def test_calculates_net_loss_when_expenses_exceed_income() -> None:
    service = ClosingService()

    net_income = service.calculate_net_income(
        income=Decimal("200.00"),
        expenses=Decimal("500.00"),
    )

    assert net_income == Decimal("-300.00")
    
def test_calculates_net_income_from_income_statement() -> None:
    
    revenue = FinancialStatementPosition(
        code="HGB.275.GKV.1",
        name="Umsatzerlöse",
        category=StatementCategory.INCOME,
    )

    expenses = FinancialStatementPosition(
        code="HGB.275.GKV.8",
        name="Sonstige betriebliche Aufwendungen",
        category=StatementCategory.EXPENSE,
    )

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name=(
                "Gewinn- und Verlustrechnung "
                "nach dem Gesamtkostenverfahren"
            ),
            children=(
                revenue,
                expenses,
            ),
        ),
        amounts={
            revenue: Decimal("500.00"),
            expenses: Decimal("200.00"),
        },
    )

    net_income = ClosingService().calculate_net_income(
        income_statement=income_statement,
    )

    assert net_income == Decimal("300.00")
    



def test_close_returns_closing_result() -> None:
    revenue = FinancialStatementPosition(
        code="HGB.275.GKV.1",
        name="Umsatzerlöse",
        category=StatementCategory.INCOME,
    )

    expense = FinancialStatementPosition(
        code="HGB.275.GKV.8",
        name="Sonstige betriebliche Aufwendungen",
        category=StatementCategory.EXPENSE,
    )

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name="GuV",
            children=(revenue, expense),
        ),
        amounts={
            revenue: Decimal("500.00"),
            expense: Decimal("200.00"),
        },
    )

    result = ClosingService().close(
        income_statement=income_statement,
    )

    assert isinstance(result, ClosingResult)
    assert result.net_income == Decimal("300.00")
    

    
   