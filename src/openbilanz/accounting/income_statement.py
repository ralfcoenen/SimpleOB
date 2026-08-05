"""Gewinn- und Verlustrechnung."""

from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.money import ZERO


class IncomeStatement:
    """Repräsentiert eine Gewinn- und Verlustrechnung."""

    def __init__(
        self,
        *,
        income_statement: FinancialStatementPosition,
        amounts: dict[FinancialStatementPosition, Decimal],
    ) -> None:
        self._income_statement = income_statement
        self._amounts = amounts

    @property
    def income_statement(self) -> FinancialStatementPosition:
        """Liefert die Wurzel der GuV."""
        return self._income_statement

    @property
    def amounts(
        self,
    ) -> dict[FinancialStatementPosition, Decimal]:
        """Liefert die berechneten Beträge."""
        return self._amounts

    def amount_for(
        self,
        position: FinancialStatementPosition,
    ) -> Decimal:
        """Liefert den Betrag einer GuV-Position."""
        return self._amounts.get(position, ZERO)
