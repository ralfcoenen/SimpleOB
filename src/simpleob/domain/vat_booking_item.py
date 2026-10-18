"""Umsatzsteuerpflichtige Rechnungsanteile."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.domain.money import ZERO, to_decimal


@dataclass(frozen=True, slots=True)
class VatBookingItem:
    """Beschreibt einen Rechnungsanteil mit Steuersatz."""

    account_number: str
    gross_amount: Decimal
    tax_rate: int

    def __post_init__(self) -> None:
        account_number = self.account_number.strip()

        if not account_number:
            raise ValueError(
                "account_number must not be blank"
            )

        gross_amount = to_decimal(
            self.gross_amount
        )

        if gross_amount <= ZERO:
            raise ValueError(
                "gross_amount must be greater than zero"
            )

        if self.tax_rate not in (0, 7, 19):
            raise ValueError(
                "tax_rate must be 0, 7 or 19"
            )

        object.__setattr__(
            self,
            "account_number",
            account_number,
        )
        object.__setattr__(
            self,
            "gross_amount",
            gross_amount,
        )
