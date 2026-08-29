"""Ausgangsumsatz für die umsatzsteuerliche Auswertung."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from openbilanz.domain.money import to_decimal
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue_kind import VatRevenueKind


@dataclass(frozen=True, slots=True)
class VatRevenue:
    """Ordnet einer Buchung einen Ausgangsumsatz zu."""

    booking_id: UUID
    gross_amount: Decimal
    revenue_kind: VatRevenueKind
    payment_kind: VatPaymentKind
    service_date: date
    revenue_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.booking_id, UUID):
            raise TypeError(
                "booking_id must be a UUID"
            )

        gross_amount = to_decimal(
            self.gross_amount
        )

        if gross_amount <= Decimal("0.00"):
            raise ValueError(
                "gross_amount must be greater than 0.00"
            )

        if not isinstance(
            self.revenue_kind,
            VatRevenueKind,
        ):
            raise TypeError(
                "revenue_kind must be a VatRevenueKind"
            )

        if not isinstance(
            self.payment_kind,
            VatPaymentKind,
        ):
            raise TypeError(
                "payment_kind must be a VatPaymentKind"
            )

        if not isinstance(self.service_date, date):
            raise TypeError(
                "service_date must be a date"
            )

        if not isinstance(self.revenue_id, UUID):
            raise TypeError(
                "revenue_id must be a UUID"
            )

        object.__setattr__(
            self,
            "gross_amount",
            gross_amount,
        )
