"""Umsatzsteuerliches Detail einer Buchungsposition."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from openbilanz.domain.money import ZERO, to_decimal
from openbilanz.domain.vat_booking_direction import (
    VatBookingDirection,
)


@dataclass(frozen=True, slots=True)
class VatBookingDetail:
    """Bewahrt die USt-relevanten Daten einer Buchungsposition."""

    booking_id: UUID
    account_number: str
    net_amount: Decimal
    tax_amount: Decimal
    tax_rate: int
    direction: VatBookingDirection

    def __post_init__(self) -> None:
        if not isinstance(self.booking_id, UUID):
            raise TypeError(
                "booking_id must be a UUID"
            )

        account_number = self.account_number.strip()

        if not account_number:
            raise ValueError(
                "account_number must not be blank"
            )

        net_amount = to_decimal(self.net_amount)
        tax_amount = to_decimal(self.tax_amount)

        if self.tax_rate not in (0, 7, 19):
            raise ValueError(
                "tax_rate must be 0, 7 or 19"
            )

        if not isinstance(
            self.direction,
            VatBookingDirection,
        ):
            raise TypeError(
                "direction must be a VatBookingDirection"
            )

        if net_amount == ZERO:
            raise ValueError(
                "net_amount must not be zero"
            )

        object.__setattr__(
            self,
            "account_number",
            account_number,
        )
        object.__setattr__(
            self,
            "net_amount",
            net_amount,
        )
        object.__setattr__(
            self,
            "tax_amount",
            tax_amount,
        )
