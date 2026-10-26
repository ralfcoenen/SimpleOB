"""Gebuchte Ausgangsrechnung auf Ziel und zugehöriger Forderungs-OP."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal


@dataclass(frozen=True, slots=True)
class ReceivableInvoice:
    """Eine Ausgangsrechnung mit einer Hauptbuchbuchung."""

    company_id: UUID
    partner_id: UUID
    invoice_number: str
    invoice_date: date
    due_date: date
    gross_amount: Decimal
    booking_id: UUID
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
        invoice_number = self.invoice_number.strip()
        if not invoice_number:
            raise ValueError("Die Rechnungsnummer darf nicht leer sein.")
        amount = to_decimal(self.gross_amount)
        if amount <= ZERO:
            raise ValueError("Der Rechnungsbetrag muss größer als 0,00 sein.")
        object.__setattr__(self, "invoice_number", invoice_number)
        object.__setattr__(self, "gross_amount", amount)


@dataclass(frozen=True, slots=True)
class ReceivableOpenItem:
    """Der unveränderliche Ursprungsbetrag einer Kundenforderung."""

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
