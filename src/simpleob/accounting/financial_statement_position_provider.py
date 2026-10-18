"""Schnittstelle für den Zugriff auf Abschlusspositionen."""

from typing import Protocol

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


class FinancialStatementPositionProvider(Protocol):
    """Liefert Abschlusspositionen anhand ihres Codes."""

    def get(
        self,
        code: str,
    ) -> FinancialStatementPosition:
        """Liefert die Abschlussposition zum angegebenen Code."""
        ...
