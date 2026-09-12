"""Jahresbezogene BVV-Daten."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class BvvAnnualData:
    """Jahresbezogene Angaben für den Betriebsvermögensvergleich."""

    previous_hgb_equity: Decimal | None
    contribution: Decimal
    withdrawal_distribution: Decimal

    def __post_init__(self) -> None:
        previous_hgb_equity = self.previous_hgb_equity

        if previous_hgb_equity is not None:
            previous_hgb_equity = to_decimal(
                previous_hgb_equity
            )

        contribution = to_decimal(
            self.contribution
        )
        withdrawal_distribution = to_decimal(
            self.withdrawal_distribution
        )

        if contribution < Decimal("0.00"):
            raise ValueError(
                "contribution must not be negative"
            )

        if withdrawal_distribution < Decimal("0.00"):
            raise ValueError(
                "withdrawal_distribution must not be negative"
            )

        object.__setattr__(
            self,
            "previous_hgb_equity",
            previous_hgb_equity,
        )
        object.__setattr__(
            self,
            "contribution",
            contribution,
        )
        object.__setattr__(
            self,
            "withdrawal_distribution",
            withdrawal_distribution,
        )
