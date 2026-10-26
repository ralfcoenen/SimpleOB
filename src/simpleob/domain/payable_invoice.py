"""Gebuchte Eingangsrechnung und zugehöriger Verbindlichkeits-OP."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal


class DuplicateSupplierInvoiceError(ValueError):
    """Eine Rechnungsnummer existiert für diesen Lieferanten bereits."""

    def __init__(self, invoice_number: str) -> None:
        self.invoice_number = invoice_number
        super().__init__(
            "Für diesen Lieferanten ist die Rechnungsnummer "
            f"{invoice_number!r} bereits erfasst. Eine erneute Erfassung "
            "benötigt eine ausdrückliche Begründung."
        )


@dataclass(frozen=True, slots=True)
class PayableInvoice:
    """Eine Eingangsrechnung mit einer Hauptbuchbuchung."""

    company_id: UUID
    partner_id: UUID
    invoice_number: str
    invoice_date: date
    due_date: date
    gross_amount: Decimal
    booking_id: UUID
    duplicate_reason: str | None = None
    invoice_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        for field_name in (
            "company_id",
            "partner_id",
            "booking_id",
            "invoice_id",
        ):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if not isinstance(self.invoice_date, date):
            raise TypeError("invoice_date must be a date")
        if not isinstance(self.due_date, date):
            raise TypeError("due_date must be a date")
        if not isinstance(self.invoice_number, str):
            raise TypeError("invoice_number must be a str")
        invoice_number = self.invoice_number.strip()
        if not invoice_number:
            raise ValueError("Die Rechnungsnummer darf nicht leer sein.")
        amount = to_decimal(self.gross_amount)
        if amount <= ZERO:
            raise ValueError("Der Rechnungsbetrag muss größer als 0,00 sein.")
        reason = self.duplicate_reason
        if reason is not None:
            if not isinstance(reason, str):
                raise TypeError("duplicate_reason must be a str or None")
            reason = reason.strip() or None
        object.__setattr__(self, "invoice_number", invoice_number)
        object.__setattr__(self, "gross_amount", amount)
        object.__setattr__(self, "duplicate_reason", reason)


@dataclass(frozen=True, slots=True)
class PayableOpenItem:
    """Unveränderlicher Ursprungsbetrag einer Lieferantenverbindlichkeit."""

    invoice_id: UUID
    amount: Decimal
    open_item_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.invoice_id, UUID):
            raise TypeError("invoice_id must be a UUID")
        if not isinstance(self.open_item_id, UUID):
            raise TypeError("open_item_id must be a UUID")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der OP-Betrag muss größer als 0,00 sein.")
        object.__setattr__(self, "amount", amount)
