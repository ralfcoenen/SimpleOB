"""Read Model für eine Zeile eines Kontoblatts."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.accounting.ledger_entry import LedgerEntry


@dataclass(frozen=True, slots=True)
class AccountStatementLine:
    """Eine einzelne Zeile eines Kontoblatts."""

    entry: LedgerEntry
    running_balance: Decimal

    def __post_init__(self) -> None:
        """Validiert die Kontoblattzeile."""

        if not isinstance(self.entry, LedgerEntry):
            raise TypeError("entry must be a LedgerEntry")
        
        if not isinstance(self.running_balance, Decimal):
            raise TypeError("running_balance must be a Decimal")