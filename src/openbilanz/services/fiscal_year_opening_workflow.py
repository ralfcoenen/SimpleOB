"""Workflow für die Eröffnung eines Geschäftsjahres."""

from collections.abc import Mapping
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.accounting.ledger import Ledger
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from openbilanz.services.posting_service import PostingService


class FiscalYearOpeningWorkflow:
    """Koordiniert die persistente Eröffnung eines Geschäftsjahres."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        company_repository: CompanyRepository,
        transfer_service: FiscalYearTransferService,
        posting_service: PostingService,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._company_repository = company_repository
        self._transfer_service = transfer_service
        self._posting_service = posting_service

    def open(
        self,
        *,
        company_id: UUID,
        source_fiscal_year: FiscalYear,
        target_fiscal_year: FiscalYear,
        account_types: Mapping[str, AccountType],
    ) -> tuple[Booking, ...]:
        """Eröffnet ein Geschäftsjahr aus den Salden des Vorjahres."""

        if source_fiscal_year == target_fiscal_year:
            raise ValueError(
                "Quell- und Zielgeschäftsjahr "
                "dürfen nicht identisch sein."
            )

        if (
            source_fiscal_year.end_date
            + timedelta(days=1)
            != target_fiscal_year.start_date
        ):
            raise ValueError(
                "Quellgeschäftsjahr geht dem Zielgeschäftsjahr "
                "nicht unmittelbar voraus."
            )

        try:
            managed_fiscal_years_before_lock = (
                self._company_repository.get_managed_fiscal_years(
                    company_id
                )
            )

            target_before_lock = next(
                (
                    managed
                    for managed in managed_fiscal_years_before_lock
                    if managed.fiscal_year == target_fiscal_year
                ),
                None,
            )

            if target_before_lock is None:
                raise ValueError(
                    "Zielgeschäftsjahr wurde nicht gefunden."
                )

            if target_before_lock.is_closed:
                raise ValueError(
                    "Zielgeschäftsjahr ist bereits abgeschlossen."
                )

            self._company_repository.lock_open_fiscal_year(
                company_id,
                target_fiscal_year,
            )

            managed_fiscal_years = (
                self._company_repository.get_managed_fiscal_years(
                    company_id
                )
            )

            source_managed_fiscal_year = next(
                (
                    managed
                    for managed in managed_fiscal_years
                    if managed.fiscal_year == source_fiscal_year
                ),
                None,
            )

            if source_managed_fiscal_year is None:
                raise ValueError(
                    "Quellgeschäftsjahr wurde nicht gefunden."
                )

            if not source_managed_fiscal_year.is_closed:
                raise ValueError(
                    "Quellgeschäftsjahr ist nicht abgeschlossen."
                )

            target_managed_fiscal_year = next(
                (
                    managed
                    for managed in managed_fiscal_years
                    if managed.fiscal_year == target_fiscal_year
                ),
                None,
            )

            if target_managed_fiscal_year is None:
                raise ValueError(
                    "Zielgeschäftsjahr wurde nicht gefunden."
                )

            if target_managed_fiscal_year.is_closed:
                raise ValueError(
                    "Zielgeschäftsjahr ist bereits abgeschlossen."
                )

            if target_managed_fiscal_year.has_opening_source:
                raise ValueError(
                    "Zielgeschäftsjahr wurde bereits eröffnet."
                )

            existing_bookings = (
                self._booking_repository.list_for_fiscal_year(
                    company_id=company_id,
                    fiscal_year=target_fiscal_year,
                )
            )

            if any(
                booking.booking_type is BookingType.OPENING
                for booking in existing_bookings
            ):
                raise ValueError(
                    "Für dieses Geschäftsjahr sind bereits "
                    "Eröffnungsbuchungen vorhanden."
                )

            source_bookings = (
                self._booking_repository.list_for_fiscal_year(
                    company_id=company_id,
                    fiscal_year=source_fiscal_year,
                )
            )

            source_ledger = Ledger()

            for booking in source_bookings:
                self._posting_service.post_booking(
                    booking=booking,
                    ledger=source_ledger,
                )

            opening_bookings = (
                self._transfer_service.create_opening_bookings(
                    ledger=source_ledger,
                    account_types=dict(account_types),
                    opening_date=target_fiscal_year.start_date,
                )
            )

            for booking in opening_bookings:
                self._booking_repository.add(
                    company_id=company_id,
                    fiscal_year=target_fiscal_year,
                    booking=booking,
                    commit=False,
                )

            self._company_repository.set_opening_source(
                company_id,
                target_fiscal_year,
                source_fiscal_year,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

        return opening_bookings
