"""Normalisierte Bankumsätze und ihre unveränderten CSV-Quelldaten."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from re import fullmatch

from simpleob.domain.money import to_decimal


class BankImportSource(str, Enum):
    """Unterstützte Importquellen."""

    QONTO_CSV = "qonto_csv"


class TransactionImportStatus(str, Enum):
    """Fachlicher Importstatus eines eingelesenen Umsatzes."""

    READY = "ready"
    NOT_SETTLED = "not_settled"


@dataclass(frozen=True, slots=True)
class BankTransactionCsvRecord:
    """Originalwerte einer CSV-Zeile einschließlich Quellzeilennummer."""

    line_number: int
    headers: tuple[str, ...]
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.line_number < 2:
            raise ValueError("Die CSV-Zeilennummer muss mindestens 2 sein.")
        if len(self.headers) != len(self.values):
            raise ValueError("CSV-Kopfzeile und Werte haben verschiedene Längen.")

    def value(self, header: str) -> str | None:
        """Liefert einen unveränderten Originalwert nach Spaltenname."""
        try:
            index = self.headers.index(header)
        except ValueError:
            return None
        return self.values[index]


@dataclass(frozen=True, slots=True)
class BankTransaction:
    """Normalisierte Banktransaktion mit separat erhaltenem Quellrecord."""

    import_source: BankImportSource
    external_transaction_id: str
    booking_date: date
    transaction_date: date | None
    counterparty: str | None
    reference: str | None
    amount: Decimal
    currency: str
    transaction_status: str
    import_validation_status: TransactionImportStatus
    source_record: BankTransactionCsvRecord

    def __post_init__(self) -> None:
        if not isinstance(self.import_source, BankImportSource):
            raise TypeError("import_source muss eine BankImportSource sein.")
        if not isinstance(self.external_transaction_id, str) or not self.external_transaction_id.strip():
            raise ValueError("Die externe Transaktions-ID darf nicht leer sein.")
        if not isinstance(self.booking_date, date) or isinstance(self.booking_date, datetime):
            raise TypeError("Das Buchungsdatum muss ein Datum sein.")
        if self.transaction_date is not None and (
            not isinstance(self.transaction_date, date)
            or isinstance(self.transaction_date, datetime)
        ):
            raise TypeError("Das Transaktionsdatum muss ein Datum oder None sein.")
        if not isinstance(self.amount, Decimal):
            raise TypeError("Der Transaktionsbetrag muss als Decimal vorliegen.")
        normalized_amount = to_decimal(self.amount)
        if normalized_amount != self.amount:
            raise ValueError("Der Transaktionsbetrag darf keine Bruchteile eines Cents enthalten.")
        if not isinstance(self.currency, str) or not fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("Die Währung muss aus drei Großbuchstaben bestehen.")
        if not isinstance(self.transaction_status, str) or not self.transaction_status.strip():
            raise ValueError("Der Transaktionsstatus darf nicht leer sein.")
        if not isinstance(self.import_validation_status, TransactionImportStatus):
            raise TypeError("Ungültiger Importvalidierungsstatus.")
        if not isinstance(self.source_record, BankTransactionCsvRecord):
            raise TypeError("source_record muss ein BankTransactionCsvRecord sein.")

        object.__setattr__(self, "external_transaction_id", self.external_transaction_id.strip())
        object.__setattr__(self, "counterparty", _optional_text(self.counterparty))
        object.__setattr__(self, "reference", _optional_text(self.reference))
        object.__setattr__(self, "amount", normalized_amount)


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
