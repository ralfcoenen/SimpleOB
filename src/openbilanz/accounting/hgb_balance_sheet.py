from dataclasses import dataclass
from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


@dataclass(frozen=True, slots=True)
class HgbBalanceSheet:
    assets: FinancialStatementPosition
    liabilities: FinancialStatementPosition
    amounts: dict[FinancialStatementPosition, Decimal]
    
    