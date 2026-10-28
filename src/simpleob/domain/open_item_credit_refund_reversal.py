"""Unveränderliche Rücknahme einer Guthabenrückerstattung."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.open_item_offset import OffsetDirection


@dataclass(frozen=True, slots=True)
class OpenItemCreditRefundReversalCandidate:
    """Lesbare Auswahlansicht einer noch nicht zurückgenommenen Erstattung."""

    refund_id: UUID
    partner_id: UUID
    partner_name: str
    direction: OffsetDirection
    amount: Decimal
    refund_date: date
    booking_date: date
    original_booking_id: UUID
    original_voucher_no: str | None
    journal_reversal_count: int
    journal_reversal_booking_id: UUID | None = None
    journal_reversal_booking_date: date | None = None

    @property
    def has_journal_reversal(self) -> bool:
        return self.journal_reversal_count > 0


@dataclass(frozen=True, slots=True)
class OpenItemCreditRefundReversal:
    """Vollständige Rücknahme mit der maßgeblichen Journalgegenbuchung."""

    company_id: UUID
    partner_id: UUID
    open_item_id: UUID
    refund_id: UUID
    direction: OffsetDirection
    reversal_booking_id: UUID
    booking_date: date
    amount: Decimal
    reason: str
    created_booking: bool
    reversal_id: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in (
            "company_id",
            "partner_id",
            "open_item_id",
            "refund_id",
            "reversal_booking_id",
            "reversal_id",
        ):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"{field_name} must be a UUID")
        if not isinstance(self.direction, OffsetDirection):
            raise TypeError("direction must be an OffsetDirection")
        if not isinstance(self.booking_date, date):
            raise TypeError("booking_date must be a date")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        if not isinstance(self.created_booking, bool):
            raise TypeError("created_booking must be a boolean")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Der Rücknahmegrund darf nicht leer sein.")
        amount = to_decimal(self.amount)
        if amount <= ZERO:
            raise ValueError("Der Rücknahmebetrag muss größer als 0,00 sein.")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "reason", self.reason.strip())
