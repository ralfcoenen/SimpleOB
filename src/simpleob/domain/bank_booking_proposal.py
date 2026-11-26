"""Bearbeitbare, noch nicht übernommene Buchungsvorschläge für Bankumsätze."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from simpleob.domain.bank_transaction import (
    BankTransaction,
    TransactionImportStatus,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class CounterBookingLineProposal:
    """Eine editierbare Gegenzeile; Konto bleibt bis zur Auswahl optional."""

    account_number: str | None
    amount: Decimal

    def __post_init__(self) -> None:
        account_number = self.account_number
        if account_number is not None:
            if not isinstance(account_number, str):
                raise TypeError("Die Kontonummer muss eine Zeichenkette oder None sein.")
            account_number = account_number.strip() or None
        if not isinstance(self.amount, Decimal):
            raise TypeError("Der Gegenbetrag muss als Decimal vorliegen.")
        amount = to_decimal(self.amount)
        if amount != self.amount or amount <= Decimal("0.00"):
            raise ValueError("Der Gegenbetrag muss positiv und centgenau sein.")
        object.__setattr__(self, "account_number", account_number)
        object.__setattr__(self, "amount", amount)


@dataclass(slots=True)
class BankBookingProposal:
    """Bearbeitbarer Vorschlag, der erst nach Validierung ein Booking ergibt."""

    transaction: BankTransaction
    bank_account_number: str | None
    booking_date: date
    description: str
    counter_lines: tuple[CounterBookingLineProposal, ...]
    _validation_errors: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.transaction, BankTransaction):
            raise TypeError("transaction muss eine BankTransaction sein.")
        if self.bank_account_number is not None:
            if not isinstance(self.bank_account_number, str):
                raise TypeError("Die Bankkontonummer muss eine Zeichenkette oder None sein.")
            self.bank_account_number = self.bank_account_number.strip() or None
        if not isinstance(self.booking_date, date) or isinstance(self.booking_date, datetime):
            raise TypeError("Das Buchungsdatum muss ein Datum sein.")
        if not isinstance(self.description, str):
            raise TypeError("Der Buchungstext muss eine Zeichenkette sein.")
        self.description = self.description.strip()
        self.counter_lines = tuple(self.counter_lines)
        if not all(isinstance(line, CounterBookingLineProposal) for line in self.counter_lines):
            raise TypeError("Alle Gegenzeilen müssen CounterBookingLineProposal sein.")

    @property
    def validation_errors(self) -> tuple[str, ...]:
        """Liefert aktuelle Validierungsfehler für die bearbeitbaren Felder."""
        errors: list[str] = []
        if self.transaction.import_validation_status is not TransactionImportStatus.READY:
            errors.append("Die Transaktion ist nicht endgültig abgewickelt.")
        if self.bank_account_number is None or not self.bank_account_number.strip():
            errors.append("Es wurde kein Bank-Sachkonto ausgewählt.")
        if not self.description:
            errors.append("Der Buchungstext darf nicht leer sein.")
        if not self.counter_lines:
            errors.append("Mindestens eine Gegenbuchungszeile ist erforderlich.")
        for index, line in enumerate(self.counter_lines, start=1):
            if line.account_number is None:
                errors.append(f"Für Gegenzeile {index} wurde kein Konto ausgewählt.")
        counter_total = sum((line.amount for line in self.counter_lines), Decimal("0.00"))
        if counter_total != abs(self.transaction.amount):
            errors.append(
                "Die Summe der Gegenbuchungszeilen stimmt nicht mit dem Bankbetrag überein."
            )
        return tuple(errors)

    @property
    def is_valid(self) -> bool:
        return not self.validation_errors

    def to_booking(self) -> Booking:
        """Erzeugt ein unpersistiertes Booking gemäß der Testformat-Vorzeichenannahme."""
        errors = self.validation_errors
        if errors:
            raise ValueError("Buchungsvorschlag ist ungültig: " + " ".join(errors))

        assert self.bank_account_number is not None
        if self.transaction.amount > Decimal("0.00"):
            lines = [
                BookingLine(self.bank_account_number, EntrySide.DEBIT, abs(self.transaction.amount))
            ]
            lines.extend(
                BookingLine(line.account_number, EntrySide.CREDIT, line.amount)
                for line in self.counter_lines
                if line.account_number is not None
            )
        else:
            lines = [
                BookingLine(line.account_number, EntrySide.DEBIT, line.amount)
                for line in self.counter_lines
                if line.account_number is not None
            ]
            lines.append(
                BookingLine(self.bank_account_number, EntrySide.CREDIT, abs(self.transaction.amount))
            )
        return Booking(
            booking_date=self.booking_date,
            description=self.description,
            lines=tuple(lines),
        )


def build_booking_proposals(
    transactions: tuple[BankTransaction, ...],
) -> tuple[BankBookingProposal, ...]:
    """Erzeugt Vorschläge nur für eindeutige, endgültig abgewickelte Umsätze."""
    proposals = []
    for transaction in transactions:
        if transaction.import_validation_status is not TransactionImportStatus.READY:
            continue
        proposals.append(
            BankBookingProposal(
                transaction=transaction,
                bank_account_number=None,
                booking_date=transaction.booking_date,
                description=" ".join(
                    text for text in (transaction.counterparty, transaction.reference) if text
                ),
                counter_lines=(
                    CounterBookingLineProposal(
                        account_number=None,
                        amount=abs(transaction.amount),
                    ),
                ),
            )
        )
    return tuple(proposals)
