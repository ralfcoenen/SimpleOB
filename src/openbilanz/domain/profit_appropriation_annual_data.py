"""Jahresbezogene Daten zur Ergebnisverwendung."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class ProfitAppropriationAnnualData:
    """Jahresbezogene Angaben zur Ergebnisverwendung."""

    statutory_reserve: Decimal
    other_revenue_reserves: Decimal
    distribution: Decimal
    profit_loss_carryforward: Decimal

    def __post_init__(self) -> None:
        statutory_reserve = to_decimal(self.statutory_reserve)
        other_revenue_reserves = to_decimal(
            self.other_revenue_reserves
        )
        distribution = to_decimal(self.distribution)
        profit_loss_carryforward = to_decimal(
            self.profit_loss_carryforward
        )

        nonnegative_values = (
            ("statutory_reserve", statutory_reserve),
            ("other_revenue_reserves", other_revenue_reserves),
            ("distribution", distribution),
        )

        for name, value in nonnegative_values:
            if value < Decimal("0.00"):
                raise ValueError(
                    f"{name} must not be negative"
                )

        object.__setattr__(
            self,
            "statutory_reserve",
            statutory_reserve,
        )
        object.__setattr__(
            self,
            "other_revenue_reserves",
            other_revenue_reserves,
        )
        object.__setattr__(
            self,
            "distribution",
            distribution,
        )
        object.__setattr__(
            self,
            "profit_loss_carryforward",
            profit_loss_carryforward,
        )
