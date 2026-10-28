"""Tatsächliche Rückerstattung eines einzelnen Guthaben-OPs."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.open_item_offset import OffsetDirection


@dataclass(frozen=True, slots=True)
class OpenItemCreditRefund:
    """Unveränderlicher Rückerstattungsvorgang mit Hauptbuchreferenz."""

    company_id: UUID
    partner_id: UUID
    open_item_id: UUID
    direction: OffsetDirection
    amount: Decimal
    refund_date: date
    booking_id: UUID
    refund_id: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in (
            "company_id",
            "partner_id",
            "open_item_id",
            "booking_id",
            "refund_id",
        ):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if not isinstance(self.direction, OffsetDirection):
            raise TypeError("direction must be an OffsetDirection")
        if not isinstance(self.refund_date, date):
            raise TypeError("refund_date must be a date")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der Rückerstattungsbetrag muss größer als 0,00 sein.")
        object.__setattr__(self, "amount", amount)
