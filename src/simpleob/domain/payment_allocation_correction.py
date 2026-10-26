"""Begründete Korrektur einer Zahlung-zu-Rechnungs-OP-Zuordnung."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.open_item_payment import PaymentDirection


@dataclass(frozen=True, slots=True)
class CorrectablePaymentAllocation:
    company_id: UUID
    partner_id: UUID
    partner_name: str
    payment_id: UUID
    payment_date: date
    payment_booking_date: date
    payment_amount: Decimal
    payment_voucher_no: str | None
    recorded_at: datetime
    direction: PaymentDirection
    original_event_id: UUID
    original_amount: Decimal
    corrected_amount: Decimal
    correctable_amount: Decimal
    source_open_item_id: UUID
    source_document_number: str


@dataclass(frozen=True, slots=True)
class PaymentAllocationCorrection:
    company_id: UUID
    partner_id: UUID
    payment_id: UUID
    original_event_id: UUID
    direction: PaymentDirection
    source_open_item_id: UUID
    target_open_item_id: UUID
    amount: Decimal
    correction_date: date
    booking_date: date
    reason: str
    booking_id: UUID | None
    correction_id: UUID = field(default_factory=uuid4)
    source_event_id: UUID = field(default_factory=uuid4)
    target_event_id: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in (
            "company_id",
            "partner_id",
            "payment_id",
            "original_event_id",
            "source_open_item_id",
            "target_open_item_id",
            "correction_id",
            "source_event_id",
            "target_event_id",
        ):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if self.booking_id is not None and not isinstance(self.booking_id, UUID):
            raise TypeError("booking_id must be a UUID or None")
        if not isinstance(self.direction, PaymentDirection):
            raise TypeError("direction must be a PaymentDirection")
        if not isinstance(self.correction_date, date):
            raise TypeError("correction_date must be a date")
        if not isinstance(self.booking_date, date):
            raise TypeError("booking_date must be a date")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Eine Begründung für die Korrektur ist erforderlich.")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der Korrekturbetrag muss größer als 0,00 sein.")
        if self.source_open_item_id == self.target_open_item_id:
            raise ValueError("Quell- und Zielrechnung müssen unterschiedlich sein.")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "reason", self.reason.strip())
