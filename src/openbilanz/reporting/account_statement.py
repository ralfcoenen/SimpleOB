"""Read Model für ein Kontoblatt."""

from dataclasses import dataclass

from openbilanz.reporting.account_statement_line import AccountStatementLine


@dataclass(frozen=True, slots=True)
class AccountStatement:
    """Ein unveränderliches Kontoblatt."""

    account_number: str
    lines: tuple[AccountStatementLine, ...]

    def __post_init__(self) -> None:
        """Validiert das Kontoblatt."""

        if not isinstance(self.account_number, str):
            raise TypeError("account_number must be a str")
    
        if not self.account_number.strip():
            raise ValueError("account_number must not be empty")
        
        object.__setattr__(
            self,
            "account_number",
            self.account_number.strip(),
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
            
