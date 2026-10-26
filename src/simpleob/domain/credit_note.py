"""Gebuchte Kunden- oder Lieferantengutschrift mit Guthaben-OP."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal


class CreditNoteKind(StrEnum):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"


class DuplicateSupplierCreditNoteError(ValueError):
    """Eine Lieferantengutschriftnummer ist für den Partner bereits erfasst."""

    def __init__(self, note_number: str) -> None:
        self.note_number = note_number
        super().__init__(
            "Für diesen Lieferanten ist die Gutschriftnummer "
            f"{note_number!r} bereits erfasst. Eine erneute Erfassung "
            "benötigt eine ausdrückliche Begründung."
        )


@dataclass(frozen=True, slots=True)
class CreditNote:
    """Eine Gutschrift mit eigener Buchung und unveränderlicher Herkunft."""

    company_id: UUID
    partner_id: UUID
    kind: CreditNoteKind
    note_number: str
    note_date: date
    gross_amount: Decimal
    booking_id: UUID
    original_invoice_id: UUID | None = None
    duplicate_reason: str | None = None
    credit_note_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        for field_name in ("company_id", "partner_id", "booking_id", "credit_note_id"):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if self.original_invoice_id is not None and not isinstance(
            self.original_invoice_id, UUID
        ):
            raise TypeError("original_invoice_id must be a UUID or None")
        if not isinstance(self.kind, CreditNoteKind):
            raise TypeError("kind must be a CreditNoteKind")
        if not isinstance(self.note_date, date):
            raise TypeError("note_date must be a date")
        if not isinstance(self.note_number, str) or not self.note_number.strip():
            raise ValueError("Die Gutschriftnummer darf nicht leer sein.")
        amount = to_decimal(self.gross_amount)
        if amount <= ZERO:
            raise ValueError("Der Gutschriftbetrag muss größer als 0,00 sein.")
        reason = self.duplicate_reason
        if reason is not None:
            if not isinstance(reason, str):
                raise TypeError("duplicate_reason must be a str or None")
            reason = reason.strip() or None
        object.__setattr__(self, "note_number", self.note_number.strip())
        object.__setattr__(self, "gross_amount", amount)
        object.__setattr__(self, "duplicate_reason", reason)


@dataclass(frozen=True, slots=True)
class CreditBalanceOpenItem:
    """Gespeicherter unveränderlicher Ursprungsbetrag eines Guthabens."""

    credit_note_id: UUID
    amount: Decimal
    open_item_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.credit_note_id, UUID):
            raise TypeError("credit_note_id must be a UUID")
        if not isinstance(self.open_item_id, UUID):
            raise TypeError("open_item_id must be a UUID")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der Guthabenbetrag muss größer als 0,00 sein.")
        object.__setattr__(self, "amount", amount)
