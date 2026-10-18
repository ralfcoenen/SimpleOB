"""HGB-Provider für Abschlusspositionen."""

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)


class HgbFinancialStatementPositionProvider(
    FinancialStatementPositionProvider,
):
    """Liefert HGB-Abschlusspositionen anhand ihres Codes."""

    def __init__(
        self,
        roots: (
            FinancialStatementPosition
            | tuple[FinancialStatementPosition, ...]
        ),
    ) -> None:
        if isinstance(roots, FinancialStatementPosition):
            self._roots = (roots,)
        else:
            self._roots = roots
    
    def get(
        self,
        code: str,
    ) -> FinancialStatementPosition:
        """Liefert die Abschlussposition zum angegebenen Code."""

        for root in self._roots:
            position = self._find_position(
                root,
                code,
            )

            if position is not None:
                return position

        raise KeyError(
            f"Unbekannter Abschlusspositionscode: {code}"
        )
       

    @staticmethod
    def _find_position(
        position: FinancialStatementPosition,
        code: str,
    ) -> FinancialStatementPosition | None:
        """Durchsucht den Abschlussbaum rekursiv."""

        if position.code == code:
            return position

        for child in position.children:
            found = (
                HgbFinancialStatementPositionProvider
                ._find_position(
                    child,
                    code,
                )
            )

            if found is not None:
                return found

        return None
