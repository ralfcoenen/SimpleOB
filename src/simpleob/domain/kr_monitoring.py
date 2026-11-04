"""Werte der informativen KR-Grenzüberwachung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from simpleob.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class KrCalendarYearTotals:
    calendar_year: int
    customer_payments: Decimal
    customer_refunds: Decimal
    has_direct_revenue_bookings: bool
    external_turnover: Decimal = ZERO
    limit: Decimal | None = None

    @property
    def balance(self) -> Decimal:
        return (
            self.customer_payments
            + self.external_turnover
            - self.customer_refunds
        )


@dataclass(frozen=True, slots=True)
class KrMonitoringSummary:
    previous_year: KrCalendarYearTotals
    current_year: KrCalendarYearTotals
    activity_start_date: date | None = None
    waiver_declared: bool = False
    waiver_date: date | None = None

    @property
    def has_direct_revenue_bookings(self) -> bool:
        return (
            self.previous_year.has_direct_revenue_bookings
            or self.current_year.has_direct_revenue_bookings
        )

    @property
    def is_visible(self) -> bool:
        return not self.waiver_declared
