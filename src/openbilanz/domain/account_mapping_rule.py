from dataclasses import dataclass

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


@dataclass(frozen=True, slots=True)
class AccountMappingRule:
    account_number: str
    debit_position: FinancialStatementPosition | None
    credit_position: FinancialStatementPosition | None

    def __post_init__(self) -> None:
        if not isinstance(self.account_number, str):
            raise TypeError("account_number must be a string")
        
        if (
                self.debit_position is None
                and self.credit_position is None
                ):
                    raise ValueError(
                    "at least one target position must be defined"
                )
                    
            