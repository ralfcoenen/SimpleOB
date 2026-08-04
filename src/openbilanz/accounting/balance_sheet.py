from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class BalanceSheet:
    assets: FinancialStatementPosition
    liabilities: FinancialStatementPosition
    amounts: Mapping[FinancialStatementPosition, Decimal]

    def __post_init__(self) -> None:
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
        