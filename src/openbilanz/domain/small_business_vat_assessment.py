"""Ergebnis der Kleinunternehmerprüfung."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.money import ZERO, to_decimal
from openbilanz.domain.small_business_vat_status import (
    SmallBusinessVatStatus,
)


@dataclass(frozen=True, slots=True)
class SmallBusinessVatAssessment:
    """Ergebnis der Prüfung nach § 19 UStG."""

    calendar_year: int
    previous_year_revenue: Decimal | None
    current_year_revenue: Decimal
    applicable_at_year_start: bool
    current_limit: Decimal
    status: SmallBusinessVatStatus

    def __post_init__(self) -> None:
        if self.calendar_year < 1:
            raise ValueError(
                "calendar_year must be greater than zero"
            )

        previous_year_revenue = (
            None
            if self.previous_year_revenue is None
            else to_decimal(
                self.previous_year_revenue
            )
        )

        current_year_revenue = to_decimal(
            self.current_year_revenue
        )
        current_limit = to_decimal(
            self.current_limit
        )

        if (
            previous_year_revenue is not None
            and previous_year_revenue < ZERO
        ):
            raise ValueError(
                "previous_year_revenue must not be negative"
            )

        if current_year_revenue < ZERO:
            raise ValueError(
                "current_year_revenue must not be negative"
            )

        if current_limit <= ZERO:
            raise ValueError(
                "current_limit must be greater than zero"
            )

        object.__setattr__(
            self,
            "previous_year_revenue",
            previous_year_revenue,
        )
        object.__setattr__(
            self,
            "current_year_revenue",
            current_year_revenue,
        )
        object.__setattr__(
            self,
            "current_limit",
            current_limit,
        )
