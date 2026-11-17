"""HGB-Ausweisumgliederung bei negativem Gesamteigenkapital."""

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.money import ZERO
from simpleob.hgb.balance_sheet_structure import (
    NON_COVERED_EQUITY_DEFICIT_CODE,
    NON_COVERED_EQUITY_OFFSET_CODE,
)


class UncoveredEquityDeficitPresentationService:
    """Erzeugt eine reine Ausweisbilanz aus einer unveränderten Rohbilanz."""

    _EQUITY_CODE = "HGB.266.PASSIVA.A"

    @classmethod
    def apply(
        cls,
        balance_sheet: BalanceSheet,
    ) -> BalanceSheet:
        """Weist einen Fehlbetrag aus, ohne Hauptbuchwerte zu verändern."""

        if not isinstance(balance_sheet, BalanceSheet):
            raise TypeError("balance_sheet muss eine BalanceSheet sein.")

        if balance_sheet.uncovered_equity_deficit_applied:
            return balance_sheet

        equity = cls._find_position(
            balance_sheet.liabilities,
            cls._EQUITY_CODE,
        )
        if equity is None:
            raise ValueError(
                "Die HGB-Eigenkapitalposition fehlt; der Fehlbetrag "
                "kann nicht sicher dargestellt werden."
            )

        equity_amount = balance_sheet.amount_for(equity)
        deficit = max(ZERO, -equity_amount)
        if deficit == ZERO:
            return balance_sheet

        if not balance_sheet.is_balanced():
            raise ValueError(
                "Der Fehlbetrag kann nur aus einer ausgeglichenen "
                "Rohbilanz ermittelt werden."
            )

        asset_position = cls._find_position(
            balance_sheet.assets,
            NON_COVERED_EQUITY_DEFICIT_CODE,
        )
        offset_position = cls._find_position(
            equity,
            NON_COVERED_EQUITY_OFFSET_CODE,
        )
        if asset_position is None or offset_position is None:
            raise ValueError(
                "Die HGB-Ausweisposition für den nicht durch "
                "Eigenkapital gedeckten Fehlbetrag fehlt."
            )

        amounts = dict(balance_sheet.amounts)
        amounts[asset_position] = deficit
        amounts[offset_position] = deficit
        amounts[equity] = equity_amount + deficit
        amounts[balance_sheet.assets] = (
            balance_sheet.amount_for(balance_sheet.assets) + deficit
        )
        amounts[balance_sheet.liabilities] = (
            balance_sheet.amount_for(balance_sheet.liabilities) + deficit
        )

        presented = BalanceSheet(
            assets=balance_sheet.assets,
            liabilities=balance_sheet.liabilities,
            amounts=amounts,
            uncovered_equity_deficit_applied=True,
        )
        if not presented.is_balanced():
            raise ValueError(
                "Die Ausweisumgliederung konnte die Bilanzgleichheit "
                "nicht erhalten."
            )
        return presented

    @classmethod
    def _find_position(
        cls,
        root: FinancialStatementPosition,
        code: str,
    ) -> FinancialStatementPosition | None:
        if root.code == code:
            return root
        for child in root.children:
            found = cls._find_position(child, code)
            if found is not None:
                return found
        return None
