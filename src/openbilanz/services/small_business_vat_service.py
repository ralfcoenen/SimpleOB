"""Fachliche Beurteilung der Kleinunternehmerregelung."""

from decimal import Decimal
from uuid import UUID

from openbilanz.domain.money import ZERO
from openbilanz.domain.small_business_vat_assessment import (
    SmallBusinessVatAssessment,
)
from openbilanz.domain.small_business_vat_limit_exceedance import (
    SmallBusinessVatLimitExceedance,
)
from openbilanz.domain.small_business_vat_status import (
    SmallBusinessVatStatus,
)
from openbilanz.services.small_business_vat_revenue_service import (
    SmallBusinessVatRevenueService,
)

_PREVIOUS_YEAR_LIMIT = Decimal("25000.00")
_CURRENT_YEAR_LIMIT = Decimal("100000.00")
_FOUNDATION_YEAR_LIMIT = Decimal("25000.00")


class SmallBusinessVatService:
    """Beurteilt die Anwendung von § 19 UStG."""

    def __init__(
        self,
        *,
        revenue_service: SmallBusinessVatRevenueService,
    ) -> None:
        self._revenue_service = revenue_service

    def assess(
        self,
        *,
        company_id: UUID,
        calendar_year: int,
        foundation_year: int,
    ) -> SmallBusinessVatAssessment:
        """Beurteilt die Kleinunternehmerregelung."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(calendar_year, int):
            raise TypeError(
                "calendar_year must be an int"
            )

        if not isinstance(foundation_year, int):
            raise TypeError(
                "foundation_year must be an int"
            )

        if calendar_year < 1:
            raise ValueError(
                "calendar_year must be greater than zero"
            )

        if foundation_year < 1:
            raise ValueError(
                "foundation_year must be greater than zero"
            )

        if foundation_year > calendar_year:
            raise ValueError(
                "foundation_year must not be after "
                "calendar_year"
            )

        current_year_revenue = (
            self._revenue_service
            .revenue_for_calendar_year(
                company_id=company_id,
                calendar_year=calendar_year,
            )
        )

        if foundation_year == calendar_year:
            status = (
                SmallBusinessVatStatus.APPLICABLE
                if (
                    current_year_revenue
                    <= _FOUNDATION_YEAR_LIMIT
                )
                else SmallBusinessVatStatus.LIMIT_EXCEEDED
            )

            return SmallBusinessVatAssessment(
                calendar_year=calendar_year,
                previous_year_revenue=None,
                current_year_revenue=current_year_revenue,
                applicable_at_year_start=True,
                current_limit=_FOUNDATION_YEAR_LIMIT,
                status=status,
            )

        previous_year_revenue = (
            self._revenue_service
            .revenue_for_calendar_year(
                company_id=company_id,
                calendar_year=calendar_year - 1,
            )
        )

        applicable_at_year_start = (
            previous_year_revenue
            <= _PREVIOUS_YEAR_LIMIT
        )

        if not applicable_at_year_start:
            return SmallBusinessVatAssessment(
                calendar_year=calendar_year,
                previous_year_revenue=previous_year_revenue,
                current_year_revenue=current_year_revenue,
                applicable_at_year_start=False,
                current_limit=_CURRENT_YEAR_LIMIT,
                status=(
                    SmallBusinessVatStatus.NOT_APPLICABLE
                ),
            )

        status = (
            SmallBusinessVatStatus.APPLICABLE
            if current_year_revenue <= _CURRENT_YEAR_LIMIT
            else SmallBusinessVatStatus.LIMIT_EXCEEDED
        )

        return SmallBusinessVatAssessment(
            calendar_year=calendar_year,
            previous_year_revenue=previous_year_revenue,
            current_year_revenue=current_year_revenue,
            applicable_at_year_start=True,
            current_limit=_CURRENT_YEAR_LIMIT,
            status=status,
        )

    def limit_exceedance(
        self,
        *,
        company_id: UUID,
        calendar_year: int,
        foundation_year: int,
    ) -> SmallBusinessVatLimitExceedance | None:
        """Liefert den ersten Umsatz oberhalb der §-19-Grenze."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(calendar_year, int):
            raise TypeError(
                "calendar_year must be an int"
            )

        if not isinstance(foundation_year, int):
            raise TypeError(
                "foundation_year must be an int"
            )

        if calendar_year < 1:
            raise ValueError(
                "calendar_year must be greater than zero"
            )

        if foundation_year < 1:
            raise ValueError(
                "foundation_year must be greater than zero"
            )

        if foundation_year > calendar_year:
            raise ValueError(
                "foundation_year must not be after "
                "calendar_year"
            )

        limit = (
            _FOUNDATION_YEAR_LIMIT
            if foundation_year == calendar_year
            else _CURRENT_YEAR_LIMIT
        )

        events = (
            self._revenue_service
            .revenue_events_for_calendar_year(
                company_id=company_id,
                calendar_year=calendar_year,
            )
        )

        running_total = ZERO

        for event in events:
            revenue_before = running_total
            running_total += event.amount

            if running_total > limit:
                return SmallBusinessVatLimitExceedance(
                    limit=limit,
                    revenue_before=revenue_before,
                    revenue_after=running_total,
                    event=event,
                )

        return None
