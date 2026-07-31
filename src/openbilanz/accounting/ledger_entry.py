"""Hauptbucheintrag für den Buchhaltungskern von OpenBilanz-UG."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from openbilanz.accounting.account_balance import ZERO, to_decimal
from openbilanz.domain.entry_side import EntrySide

@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """Repräsentiert eine einzelne Kontenbewegung im Hauptbuch."""

    booking_id: UUID
    booking_date: date
    voucher_no: str
    description: str
    account_no: str
    side: EntrySide
    amount: Decimal

    def __post_init__(self) -> None:
        """Normalisiert und validiert den Hauptbucheintrag."""

        if not isinstance(self.booking_id, UUID):
            raise TypeError("Die Buchungs-ID muss eine UUID sein.")

        if not isinstance(self.booking_date, date):
            raise TypeError("Das Buchungsdatum muss ein date-Objekt sein.")

        if not isinstance(self.side, EntrySide):
            raise TypeError("Die Buchungsseite muss ein EntrySide-Wert sein.")

        if not isinstance(self.voucher_no, str):
            raise TypeError("Die Belegnummer muss eine Zeichenkette sein.")

        if not isinstance(self.description, str):
            raise TypeError("Der Buchungstext muss eine Zeichenkette sein.")

        if not isinstance(self.account_no, str):
            raise TypeError("Die Kontonummer muss eine Zeichenkette sein.")

        normalized_voucher_no = self.voucher_no.strip()

        if not normalized_voucher_no:
            raise ValueError("Die Belegnummer darf nicht leer sein.")

        normalized_description = self.description.strip()

        if not normalized_description:
            raise ValueError("Der Buchungstext darf nicht leer sein.")

        normalized_account_no = self.account_no.strip()

        if not normalized_account_no:
            raise ValueError("Die Kontonummer darf nicht leer sein.")

        decimal_amount = to_decimal(self.amount)

        if decimal_amount <= ZERO:
            raise ValueError("Ein Buchungsbetrag muss größer als 0,00 sein.")

        object.__setattr__(self, "account_no", normalized_account_no)
        object.__setattr__(self, "amount", decimal_amount)
        object.__setattr__(self, "voucher_no", normalized_voucher_no)
        object.__setattr__(self, "description", normalized_description) 
        
        