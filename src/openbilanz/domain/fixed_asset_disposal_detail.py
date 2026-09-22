"""Fachliche Detailwerte eines Anlagenabgangs."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class FixedAssetDisposalDetail:
    """Für Auswertungen benötigte Werte eines Anlagenabgangs."""

    position_code: str
    carrying_amount: Decimal
    net_proceeds: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.position_code, str):
            raise TypeError(
                "position_code must be a string"
            )

        position_code = self.position_code.strip()

        if not position_code:
            raise ValueError(
                "position_code must not be empty"
            )

        carrying_amount = to_decimal(
            self.carrying_amount
        )
        net_proceeds = to_decimal(
            self.net_proceeds
        )

        if carrying_amount < Decimal("0.00"):
            raise ValueError(
                "carrying_amount must not be negative"
            )

        if net_proceeds < Decimal("0.00"):
            raise ValueError(
                "net_proceeds must not be negative"
            )

        object.__setattr__(
            self,
            "position_code",
            position_code,
        )
        object.__setattr__(
            self,
            "carrying_amount",
            carrying_amount,
        )
        object.__setattr__(
            self,
            "net_proceeds",
            net_proceeds,
        )
