"""Kalenderjahres-Service für die informative KR-Grenzüberwachung."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.database.company_repository import CompanyRepository
from simpleob.database.kr_monitoring_repository import KrMonitoringRepository
from simpleob.domain.kr_monitoring import KrCalendarYearTotals, KrMonitoringSummary
from simpleob.domain.kr_settings import KrSettings


class KrMonitoringService:
    def __init__(
        self,
        repository: KrMonitoringRepository,
        settings_repository: CompanyRepository,
    ) -> None:
        self._repository = repository
        self._settings_repository = settings_repository

    def get_settings(self, *, company_id: UUID) -> KrSettings:
        settings = self._settings_repository.get_kr_settings(company_id)
        return settings or KrSettings(company_id=company_id)

    def save_settings(
        self,
        settings: KrSettings,
        *,
        expected_settings: KrSettings | None = None,
    ) -> None:
        self._settings_repository.save_kr_settings(
            settings,
            expected_settings=expected_settings,
        )

    def get_summary(
        self, *, company_id: UUID, today: date | None = None
    ) -> KrMonitoringSummary:
        current_date = today or date.today()
        current_year = current_date.year
        settings = self.get_settings(company_id=company_id)
        previous_year = self._repository.get_calendar_year_totals(
            company_id=company_id,
            calendar_year=current_year - 1,
        )
        current_year_totals = self._repository.get_calendar_year_totals(
            company_id=company_id,
            calendar_year=current_year,
        )
        return KrMonitoringSummary(
            previous_year=self._with_settings(
                previous_year,
                external_turnover=settings.external_turnover_for(current_year - 1),
                activity_start_date=settings.activity_start_date,
                current_year=False,
            ),
            current_year=self._with_settings(
                current_year_totals,
                external_turnover=settings.external_turnover_for(current_year),
                activity_start_date=settings.activity_start_date,
                current_year=True,
            ),
            activity_start_date=settings.activity_start_date,
            waiver_declared=settings.waiver_declared,
            waiver_date=settings.waiver_date,
        )

    @staticmethod
    def _with_settings(
        totals: KrCalendarYearTotals,
        *,
        external_turnover: Decimal,
        activity_start_date: date | None,
        current_year: bool,
    ) -> KrCalendarYearTotals:
        limit = None
        if activity_start_date is not None:
            if totals.calendar_year >= activity_start_date.year:
                if current_year:
                    limit = Decimal(
                        "25000.00"
                        if totals.calendar_year == activity_start_date.year
                        else "100000.00"
                    )
                else:
                    limit = Decimal("25000.00")
        return KrCalendarYearTotals(
            calendar_year=totals.calendar_year,
            customer_payments=totals.customer_payments,
            customer_refunds=totals.customer_refunds,
            has_direct_revenue_bookings=totals.has_direct_revenue_bookings,
            external_turnover=external_turnover,
            limit=limit,
        )
