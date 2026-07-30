"""Read Model für ein Kontoblatt."""

from dataclasses import dataclass

from openbilanz.reporting.account_statement_line import AccountStatementLine


@dataclass(frozen=True, slots=True)
class AccountStatement:
    """Ein unveränderliches Kontoblatt."""

    account_no: str
    lines: tuple[AccountStatementLine, ...]

    def __post_init__(self) -> None:
        """Validiert das Kontoblatt."""

        if not isinstance(self.account_no, str):
            raise TypeError("account_no must be a str")
    
        if not self.account_no.strip():
            raise ValueError("account_no must not be empty")
        
        object.__setattr__(
            self,
            "account_no",
            self.account_no.strip(),
        )
        
        if not isinstance(self.lines, tuple):
            raise TypeError("lines must be a tuple")
        
        if not all(
            isinstance(line, AccountStatementLine)
            for line in self.lines
        ):
            raise TypeError(
                    "all lines must be AccountStatementLine instances"
            )
            
