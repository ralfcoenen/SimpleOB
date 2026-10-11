"""Workflow für die Bestätigung einer Ergebnisverwendungsbuchung."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.profit_appropriation_posting import (
    ProfitAppropriationPosting,
)
from openbilanz.domain.profit_appropriation_posting_proposal import (
    ProfitAppropriationPostingProposal,
)
from openbilanz.services.profit_appropriation_booking_service import (
    ProfitAppropriationBookingService,
)


class ProfitAppropriationPostingWorkflow:
    """Persistiert eine bestätigte Ergebnisverwendungsbuchung atomar."""

    def __init__(
        self,
        *,
        session: Session,
        company_repository: CompanyRepository,
        booking_repository: BookingRepository,
        posting_repository: ProfitAppropriationPostingRepository,
        booking_service: ProfitAppropriationBookingService,
    ) -> None:
        self._session = session
        self._company_repository = company_repository
        self._booking_repository = booking_repository
        self._posting_repository = posting_repository
        self._booking_service = booking_service

    def confirm(
        self,
        *,
        company_id: UUID,
        source_fiscal_year: FiscalYear,
        target_fiscal_year: FiscalYear,
        proposal: ProfitAppropriationPostingProposal,
    ) -> ProfitAppropriationPosting:
        """Bestätigt eine Ergebnisverwendungsbuchung atomar und sperrgesichert."""

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")

        if not isinstance(source_fiscal_year, FiscalYear):
            raise TypeError(
                "source_fiscal_year must be a FiscalYear"
            )

        if not isinstance(target_fiscal_year, FiscalYear):
            raise TypeError(
                "target_fiscal_year must be a FiscalYear"
            )

        if not isinstance(
            proposal,
            ProfitAppropriationPostingProposal,
        ):
            raise TypeError(
                "proposal must be a "
                "ProfitAppropriationPostingProposal"
            )

        try:
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

            if not target_managed_fiscal_year.is_open:
                raise ValueError(
                    "Zielgeschäftsjahr ist bereits abgeschlossen."
                )

            if (
                target_managed_fiscal_year.opening_source
                != source_fiscal_year
            ):
                raise ValueError(
                    "Zielgeschäftsjahr wurde nicht aus dem "
                    "Quellgeschäftsjahr eröffnet."
                )

            if not target_fiscal_year.contains(
                proposal.booking_date
            ):
                raise ValueError(
                    "Das Buchungsdatum liegt nicht im "
                    "Zielgeschäftsjahr."
                )

            existing_postings = (
                self._posting_repository
                .list_for_source_fiscal_year(
                    company_id=company_id,
                    source_fiscal_year_end=(
                        source_fiscal_year.end_date
                    ),
                )
            )

            for existing_posting in existing_postings:
                if (
                    existing_posting.posting_type
                    == proposal.posting_type
                    and not self._booking_repository.is_reversed(
                        existing_posting.booking_id
                    )
                ):
                    raise ValueError(
                        "Für diesen Ergebnisverwendungstyp "
                        "existiert bereits eine wirksame Buchung."
                    )

            booking = self._booking_service.build_booking(
                proposal=proposal
            )

            posting = ProfitAppropriationPosting(
                source_fiscal_year_end=(
                    source_fiscal_year.end_date
                ),
                posting_date=proposal.booking_date,
                amount=proposal.amount,
                booking_id=booking.booking_id,
                posting_type=proposal.posting_type,
            )

            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=target_fiscal_year,
                booking=booking,
                commit=False,
            )

            self._posting_repository.add(
                company_id=company_id,
                posting=posting,
                booking_line_position=0,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

        return posting
