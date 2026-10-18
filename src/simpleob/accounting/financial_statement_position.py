from dataclasses import dataclass, field

from simpleob.accounting.statement_category import StatementCategory


@dataclass(frozen=True, slots=True)
class FinancialStatementPosition:
    code: str
    name: str
    children: tuple["FinancialStatementPosition", ...] = field(
        default_factory=tuple
    )
    category: StatementCategory = StatementCategory.NEUTRAL