from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FinancialStatementPosition:
    code: str
    name: str
    children: tuple["FinancialStatementPosition", ...] = field(
        default_factory=tuple
    )
