"""Buchungszeilen für das Domänenmodell von OpenBilanz-UG."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.money import ZERO, to_decimal


@dataclass(frozen=True, slots=True)
class BookingLine:
    """
    Repräsentiert eine einzelne Zeile eines Buchungssatzes.

    Der Betrag ist immer positiv. Ob die Buchungszeile im Soll oder
    im Haben steht, wird ausschließlich durch ``side`` bestimmt.
    """

    account_number: str
    side: EntrySide
    amount: Decimal

    def __post_init__(self) -> None:
        """Validiert und normalisiert die Buchungszeile."""
        account_number = self._normalize_account_number(
            self.account_number
        )
        side = EntrySide.from_value(self.side)
        amount = to_decimal(self.amount)

        if amount <= ZERO:
            raise ValueError(
                "Der Betrag einer Buchungszeile muss größer als 0,00 sein."
            )

        object.__setattr__(
            self,
            "account_number",
            account_number,
        )
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "amount", amount)

    @property
    def is_debit(self) -> bool:
        """Prüft, ob die Buchungszeile auf der Sollseite steht."""
        return self.side is EntrySide.DEBIT

    @property
    def is_credit(self) -> bool:
        """Prüft, ob die Buchungszeile auf der Habenseite steht."""
        return self.side is EntrySide.CREDIT

    @staticmethod
    def _normalize_account_number(
        account_number: str,
    ) -> str:
        """
        Prüft und normalisiert die Kontonummer.

        Raises:
            TypeError:
                Wenn die Kontonummer keine Zeichenkette ist.
            ValueError:
                Wenn die Kontonummer leer ist.
        """
        if not isinstance(account_number, str):
            raise TypeError(
                "Die Kontonummer muss eine Zeichenkette sein."
            )

        normalized_account_number = account_number.strip()

        if not normalized_account_number:
            raise ValueError(
                "Die Kontonummer darf nicht leer sein."
            )

        return normalized_account_number