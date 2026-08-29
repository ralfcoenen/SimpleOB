"""Ermittlung des §-19-relevanten vereinnahmten Umsatzes."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.vat_revenue_repository import (
    VatRevenueRepository,
)
from openbilanz.domain.money import ZERO
from openbilanz.domain.small_business_vat_revenue_event import (
    SmallBusinessVatRevenueEvent,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue_kind import VatRevenueKind


class SmallBusinessVatRevenueService:
    """Ermittelt den maßgeblichen vereinnahmten Umsatz."""

    def __init__(
        self,
        *,
        vat_revenue_repository: VatRevenueRepository,
        booking_repository: BookingRepository,
    ) -> None:
        self._vat_revenue_repository = (
            vat_revenue_repository
        )
        self._booking_repository = booking_repository

    def revenue_events_for_calendar_year(
        self,
        *,
        company_id: UUID,
        calendar_year: int,
    ) -> tuple[SmallBusinessVatRevenueEvent, ...]:
        """Liefert die relevanten vereinnahmten Umsätze chronologisch."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(calendar_year, int):
            raise TypeError(
                "calendar_year must be an int"
            )

        if calendar_year < 1:
            raise ValueError(
                "calendar_year must be greater than zero"
            )

        start_date = date(
            calendar_year,
            1,
            1,
        )
        end_date = date(
            calendar_year,
            12,
            31,
        )

        revenues = (
            self._vat_revenue_repository
            .list_revenues_for_company(
                company_id=company_id,
            )
        )

        events: list[
            SmallBusinessVatRevenueEvent
        ] = []

        for revenue in revenues:
            if (
                revenue.revenue_kind
                is VatRevenueKind.FIXED_ASSET_DISPOSAL
            ):
                continue

            if (
                revenue.payment_kind
                is VatPaymentKind.IMMEDIATE
            ):
                revenue_booking = (
                    self._booking_repository.get(
                        revenue.booking_id
                    )
                )

                if revenue_booking is None:
                    raise ValueError(
                        "Die Umsatzbuchung ist nicht vorhanden."
                    )

                if (
                    start_date
                    <= revenue_booking.booking_date
                    <= end_date
                ):
                    events.append(
                        SmallBusinessVatRevenueEvent(
                            event_date=(
                                revenue_booking.booking_date
                            ),
                            amount=revenue.gross_amount,
                            revenue_id=revenue.revenue_id,
                            booking_id=revenue.booking_id,
                        )
                    )

                continue

            allocations = (
                self._vat_revenue_repository
                .list_allocations_for_revenue(
                    revenue.revenue_id
                )
            )

            for allocation in allocations:
                payment_booking = (
                    self._booking_repository.get(
                        allocation.payment_booking_id
                    )
                )

                if payment_booking is None:
                    raise ValueError(
                        "Die Zahlungsbuchung ist nicht vorhanden."
                    )

                if (
                    start_date
                    <= payment_booking.booking_date
                    <= end_date
                ):
                    events.append(
                        SmallBusinessVatRevenueEvent(
                            event_date=(
                                payment_booking.booking_date
                            ),
                            amount=allocation.amount,
                            revenue_id=revenue.revenue_id,
                            booking_id=(
                                allocation.payment_booking_id
                            ),
                        )
                    )

        return tuple(
            sorted(
                events,
                key=lambda event: (
                    event.event_date,
                    str(event.booking_id),
                ),
            )
        )

    def revenue_for_calendar_year(
        self,
        *,
        company_id: UUID,
        calendar_year: int,
    ) -> Decimal:
        """Ermittelt den relevanten Umsatz eines Kalenderjahres."""

        events = self.revenue_events_for_calendar_year(
            company_id=company_id,
            calendar_year=calendar_year,
        )

        return sum(
            (
                event.amount
                for event in events
            ),
            start=ZERO,
        )
