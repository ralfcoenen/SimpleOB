"""Grenzüberschreitung bei der Kleinunternehmerregelung."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.money import ZERO, to_decimal
from openbilanz.domain.small_business_vat_revenue_event import (
    SmallBusinessVatRevenueEvent,
)


@dataclass(frozen=True, slots=True)
class SmallBusinessVatLimitExceedance:
    """Beschreibt den Umsatz, mit dem eine §-19-Grenze überschritten wird."""

    limit: Decimal
    revenue_before: Decimal
    revenue_after: Decimal
    event: SmallBusinessVatRevenueEvent

    def __post_init__(self) -> None:
        limit = to_decimal(self.limit)
        revenue_before = to_decimal(
            self.revenue_before
        )
        revenue_after = to_decimal(
            self.revenue_after
        )

        if limit <= ZERO:
            raise ValueError(
                "limit must be greater than zero"
            )

        if revenue_before < ZERO:
            raise ValueError(
                "revenue_before must not be negative"
            )

        if revenue_after <= revenue_before:
            raise ValueError(
                "revenue_after must be greater than "
                "revenue_before"
            )

        if revenue_before > limit:
            raise ValueError(
                "revenue_before must not exceed limit"
            )

        if revenue_after <= limit:
            raise ValueError(
                "revenue_after must exceed limit"
            )

        if not isinstance(
            self.event,
            SmallBusinessVatRevenueEvent,
        ):
            raise TypeError(
                "event must be a "
                "SmallBusinessVatRevenueEvent"
            )

        object.__setattr__(
            self,
            "limit",
            limit,
        )
        object.__setattr__(
            self,
            "revenue_before",
            revenue_before,
        )
        object.__setattr__(
            self,
            "revenue_after",
            revenue_after,
        )
