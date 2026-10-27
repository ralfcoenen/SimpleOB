"""Manuelle Verrechnung eines Rechnungs-OPs mit einem Guthaben-OP."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal


class OffsetDirection(StrEnum):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"


@dataclass(frozen=True, slots=True)
class InvoiceOffsetSummary:
    company_id: UUID
    partner_id: UUID
    open_item_id: UUID
    direction: OffsetDirection
    document_number: str
    original_amount: Decimal
    open_amount: Decimal
    account_number: str


@dataclass(frozen=True, slots=True)
class CreditOffsetSummary:
    company_id: UUID
    partner_id: UUID
    open_item_id: UUID
    direction: OffsetDirection
    document_number: str
    original_amount: Decimal
    available_amount: Decimal
    account_number: str
    cancellation_booking_date: date | None = None


@dataclass(frozen=True, slots=True)
class OpenItemOffset:
    company_id: UUID
    partner_id: UUID
    direction: OffsetDirection
    invoice_open_item_id: UUID
    credit_open_item_id: UUID
    amount: Decimal
    settlement_date: date
    booking_id: UUID
    settlement_id: UUID = field(default_factory=uuid4)
    invoice_event_id: UUID = field(default_factory=uuid4)
    credit_event_id: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in (
            "company_id",
            "partner_id",
            "invoice_open_item_id",
            "credit_open_item_id",
            "booking_id",
            "settlement_id",
            "invoice_event_id",
            "credit_event_id",
        ):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if not isinstance(self.direction, OffsetDirection):
            raise TypeError("direction must be an OffsetDirection")
        if not isinstance(self.settlement_date, date):
            raise TypeError("settlement_date must be a date")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der Verrechnungsbetrag muss größer als 0,00 sein.")
        object.__setattr__(self, "amount", amount)
