"""Buchungen für das Domänenmodell von OpenBilanz-UG."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable
from uuid import UUID, uuid4

from openbilanz.domain.money import ZERO
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.errors import UnbalancedBookingError


@dataclass(frozen=True, slots=True)
class Booking:
    """
    Repräsentiert einen vollständigen Buchungssatz.

    Eine Buchung ist nach ihrer Erzeugung unveränderlich und muss
    mindestens eine Soll- sowie eine Habenzeile enthalten. Die Summen
    beider Seiten müssen übereinstimmen.
    """

    booking_date: date
    lines: tuple[BookingLine, ...]
    voucher_no: str | None = None
    description: str | None = None
    booking_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Normalisiert und validiert die Buchung."""
        booking_date = self._validate_booking_date(self.booking_date)
        lines = self._normalize_lines(self.lines)
        voucher_no = self._normalize_optional_text(
            self.voucher_no,
            field_name="Belegnummer",
        )
        description = self._normalize_optional_text(
            self.description,
            field_name="Buchungstext",
        )

        if not isinstance(self.booking_id, UUID):
            raise TypeError("Die Buchungs-ID muss eine UUID sein.")

        if len(lines) < 2:
            raise ValueError(
                "Eine Buchung muss mindestens zwei Buchungszeilen enthalten."
            )

        if not any(line.side is EntrySide.DEBIT for line in lines):
            raise ValueError("Eine Buchung muss mindestens eine Sollzeile enthalten.")

        if not any(line.side is EntrySide.CREDIT for line in lines):
            raise ValueError("Eine Buchung muss mindestens eine Habenzeile enthalten.")

        debit_total = sum(
            (line.amount for line in lines if line.side is EntrySide.DEBIT),
            start=ZERO,
        )

        credit_total = sum(
            (line.amount for line in lines if line.side is EntrySide.CREDIT),
            start=ZERO,
        )

        if debit_total != credit_total:
            raise UnbalancedBookingError("Soll- und Habensumme der Buchung müssen übereinstimmen.")

        object.__setattr__(self, "booking_date", booking_date)
        object.__setattr__(self, "lines", lines)
        object.__setattr__(self, "voucher_no", voucher_no)
        object.__setattr__(self, "description", description)

    @property
    def debit_total(self) -> Decimal:
        """Gibt die Summe aller Sollzeilen zurück."""
        return sum(
            (line.amount for line in self.lines if line.side is EntrySide.DEBIT),
            start=ZERO,
        )

    @property
    def credit_total(self) -> Decimal:
        """Gibt die Summe aller Habenzeilen zurück."""
        return sum(
            (line.amount for line in self.lines if line.side is EntrySide.CREDIT),
            start=ZERO,
        )

    @property
    def is_balanced(self) -> bool:
        """Prüft, ob Soll- und Habensumme übereinstimmen."""
        return self.debit_total == self.credit_total

    @property
    def debit_lines(self) -> tuple[BookingLine, ...]:
        """Gibt alle Sollzeilen zurück."""
        return tuple(line for line in self.lines if line.side is EntrySide.DEBIT)

    @property
    def credit_lines(self) -> tuple[BookingLine, ...]:
        """Gibt alle Habenzeilen zurück."""
        return tuple(line for line in self.lines if line.side is EntrySide.CREDIT)

    def __iter__(self):
        """Ermöglicht die Iteration über die Buchungszeilen."""
        return iter(self.lines)

    def __len__(self) -> int:
        """Gibt die Anzahl der Buchungszeilen zurück."""
        return len(self.lines)

    @staticmethod
    def _validate_booking_date(value: date) -> date:
        """Prüft das Buchungsdatum."""
        if not isinstance(value, date):
            raise TypeError("Das Buchungsdatum muss ein Datum sein.")

        return value

    @staticmethod
    def _normalize_lines(
        value: Iterable[BookingLine],
    ) -> tuple[BookingLine, ...]:
        """Normalisiert die Buchungszeilen zu einem Tupel."""
        if isinstance(value, (str, bytes)):
            raise TypeError(
                "Die Buchungszeilen müssen eine Sammlung von BookingLine-Objekten sein."
            )

        try:
            lines = tuple(value)
        except TypeError as exc:
            raise TypeError("Die Buchungszeilen müssen iterierbar sein.") from exc

        if not all(isinstance(line, BookingLine) for line in lines):
            raise TypeError("Alle Buchungszeilen müssen BookingLine-Objekte sein.")

        return lines

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
        *,
        field_name: str,
    ) -> str | None:
        """Normalisiert optionale Textfelder."""
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(f"{field_name} muss eine Zeichenkette sein.")

        normalized_value = value.strip()

        if not normalized_value:
            return None

        return normalized_value
