"""Vereinnahmtes Ereignis für die §-19-Umsatzermittlung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class SmallBusinessVatRevenueEvent:
    """Ein tatsächlich vereinnahmter §-19-relevanter Umsatz."""

    event_date: date
    amount: Decimal
    revenue_id: UUID
    booking_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.event_date, date):
            raise TypeError(
                "event_date must be a date"
            )

        amount = to_decimal(
            self.amount
        )

        if amount <= Decimal("0.00"):
            raise ValueError(
                "amount must be greater than 0.00"
            )

        if not isinstance(self.revenue_id, UUID):
            raise TypeError(
                "revenue_id must be a UUID"
            )

        if not isinstance(self.booking_id, UUID):
            raise TypeError(
                "booking_id must be a UUID"
            )

        object.__setattr__(
            self,
            "amount",
            amount,
        )
