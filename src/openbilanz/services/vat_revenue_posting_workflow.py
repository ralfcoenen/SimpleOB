"""Atomare Verbuchung umsatzsteuerlicher Buchungen."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.vat_booking_detail_repository import (
    VatBookingDetailRepository,
)
from openbilanz.database.vat_revenue_repository import (
    VatRevenueRepository,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.vat_booking_detail import VatBookingDetail
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue import VatRevenue
from openbilanz.domain.vat_revenue_kind import VatRevenueKind


class VatRevenuePostingWorkflow:
    """Persistiert USt-Buchungen mit ihren Zusatzdaten atomar."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        vat_booking_detail_repository: VatBookingDetailRepository,
        vat_revenue_repository: VatRevenueRepository,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._vat_booking_detail_repository = (
            vat_booking_detail_repository
        )
        self._vat_revenue_repository = (
            vat_revenue_repository
        )

    def post_booking(
        self,
        *,
        company: Company,
        fiscal_year: FiscalYear,
        booking: Booking,
        booking_details: tuple[VatBookingDetail, ...],
    ) -> None:
        """Persistiert USt-Buchung und USt-Details gemeinsam."""

        try:
            self._booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )

            self._vat_booking_detail_repository.add_details(
                booking_details,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

    def post(
        self,
        *,
        company: Company,
        fiscal_year: FiscalYear,
        booking: Booking,
        booking_details: tuple[VatBookingDetail, ...],
        gross_amount: Decimal,
        revenue_kind: VatRevenueKind,
        payment_kind: VatPaymentKind,
        service_date: date,
    ) -> VatRevenue:
        """Persistiert Buchung, USt-Details und Ausgangsumsatz gemeinsam."""

        revenue = VatRevenue(
            booking_id=booking.booking_id,
            gross_amount=gross_amount,
            revenue_kind=revenue_kind,
            payment_kind=payment_kind,
            service_date=service_date,
        )

        try:
            self._booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )

            self._vat_booking_detail_repository.add_details(
                booking_details,
                commit=False,
            )

            self._vat_revenue_repository.add_revenue(
                revenue,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

        return revenue
