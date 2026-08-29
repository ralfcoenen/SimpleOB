"""Zuordnung einer Zahlung zu einem Ausgangsumsatz."""

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class VatPaymentAllocation:
    """Ordnet eine Zahlung einem Ausgangsumsatz zu."""

    revenue_id: UUID
    payment_booking_id: UUID
    amount: Decimal
    allocation_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.revenue_id, UUID):
            raise TypeError(
                "revenue_id must be a UUID"
            )

        if not isinstance(
            self.payment_booking_id,
            UUID,
        ):
            raise TypeError(
                "payment_booking_id must be a UUID"
            )

        amount = to_decimal(self.amount)

        if amount <= Decimal("0.00"):
            raise ValueError(
                "amount must be greater than 0.00"
            )

        if not isinstance(self.allocation_id, UUID):
            raise TypeError(
                "allocation_id must be a UUID"
            )

        object.__setattr__(
            self,
            "amount",
            amount,
        )
