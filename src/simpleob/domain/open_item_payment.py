"""Zahlung und Zuordnung zu genau einem Rechnungs-OP."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal


class PaymentDirection(StrEnum):
    CUSTOMER_RECEIPT = "CUSTOMER_RECEIPT"
    SUPPLIER_PAYMENT = "SUPPLIER_PAYMENT"


@dataclass(frozen=True, slots=True)
class OpenInvoiceSummary:
    """Für die Erfassung einer Zahlung verwendbare offene Rechnung."""

    company_id: UUID
    partner_id: UUID
    open_item_id: UUID
    direction: PaymentDirection
    document_number: str
    document_date: date
    due_date: date
    original_amount: Decimal
    open_amount: Decimal
    partner_name: str


@dataclass(frozen=True, slots=True)
class OpenItemPayment:
    """Ein tatsächlicher Zahlungsvorgang mit Hauptbuchreferenz."""

    company_id: UUID
    partner_id: UUID
    direction: PaymentDirection
    amount: Decimal
    payment_date: date
    booking_id: UUID
    payment_id: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in ("company_id", "partner_id", "booking_id", "payment_id"):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if not isinstance(self.direction, PaymentDirection):
            raise TypeError("direction must be a PaymentDirection")
        if not isinstance(self.payment_date, date):
            raise TypeError("payment_date must be a date")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der Zahlungsbetrag muss größer als 0,00 sein.")
        object.__setattr__(self, "amount", amount)


@dataclass(frozen=True, slots=True)
class OpenItemPaymentEvent:
    """Unveränderliche Zuordnung einer Zahlung zu genau einem Rechnungs-OP."""

    payment_id: UUID
    open_item_id: UUID
    direction: PaymentDirection
    amount: Decimal
    effective_date: date
    event_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        for field_name in ("payment_id", "open_item_id", "event_id"):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if not isinstance(self.direction, PaymentDirection):
            raise TypeError("direction must be a PaymentDirection")
        if not isinstance(self.effective_date, date):
            raise TypeError("effective_date must be a date")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der Zuordnungsbetrag muss größer als 0,00 sein.")
        object.__setattr__(self, "amount", amount)
