from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class BalanceSheet:
    assets: FinancialStatementPosition
    liabilities: FinancialStatementPosition
    amounts: Mapping[FinancialStatementPosition, Decimal]
    uncovered_equity_deficit_applied: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.uncovered_equity_deficit_applied, bool):
            raise TypeError(
                "uncovered_equity_deficit_applied muss bool sein."
            )
        object.__setattr__(
            self,
            "amounts",
            MappingProxyType(dict(self.amounts)),
        )

    def amount_for(
        self,
        position: FinancialStatementPosition,
    ) -> Decimal:
        return self.amounts.get(position, ZERO)

    def is_balanced(self) -> bool:
        return (
            self.amount_for(self.assets)
            == self.amount_for(self.liabilities)
        )

    def has_nonzero_amount_in_subtree(
        self,
        position: FinancialStatementPosition,
    ) -> bool:
        """Prüft, ob diese Position oder ein Kind einen Betrag trägt."""

        if self.amount_for(position) != ZERO:
            return True

        return any(
            self.has_nonzero_amount_in_subtree(child)
            for child in position.children
        )
