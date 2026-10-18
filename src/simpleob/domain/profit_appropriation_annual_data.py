"""Jahresbezogene Daten zur Ergebnisverwendung."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class ProfitAppropriationAnnualData:
    """Jahresbezogene Angaben zur Ergebnisverwendung."""

    statutory_reserve_addition: Decimal
    other_revenue_reserves_addition: Decimal
    statutory_reserve_release: Decimal
    other_revenue_reserves_release: Decimal
    distribution: Decimal
    profit_loss_carryforward: Decimal

    def __post_init__(self) -> None:
        statutory_reserve_addition = to_decimal(
            self.statutory_reserve_addition
        )
        other_revenue_reserves_addition = to_decimal(
            self.other_revenue_reserves_addition
        )
        statutory_reserve_release = to_decimal(
            self.statutory_reserve_release
        )
        other_revenue_reserves_release = to_decimal(
            self.other_revenue_reserves_release
        )
        distribution = to_decimal(self.distribution)
        profit_loss_carryforward = to_decimal(
            self.profit_loss_carryforward
        )

        nonnegative_values = (
            (
                "statutory_reserve_addition",
                statutory_reserve_addition,
            ),
            (
                "other_revenue_reserves_addition",
                other_revenue_reserves_addition,
            ),
            (
                "statutory_reserve_release",
                statutory_reserve_release,
            ),
            (
                "other_revenue_reserves_release",
                other_revenue_reserves_release,
            ),
            ("distribution", distribution),
        )

        for name, value in nonnegative_values:
            if value < Decimal("0.00"):
                raise ValueError(
                    f"{name} must not be negative"
                )

        object.__setattr__(
            self,
            "statutory_reserve_addition",
            statutory_reserve_addition,
        )
        object.__setattr__(
            self,
            "other_revenue_reserves_addition",
            other_revenue_reserves_addition,
        )
        object.__setattr__(
            self,
            "statutory_reserve_release",
            statutory_reserve_release,
        )
        object.__setattr__(
            self,
            "other_revenue_reserves_release",
            other_revenue_reserves_release,
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
