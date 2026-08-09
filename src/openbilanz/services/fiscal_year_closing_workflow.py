"""Workflow für den persistenten Jahresabschluss."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService


class FiscalYearClosingWorkflow:
    """Koordiniert den persistenten Abschluss eines Geschäftsjahres."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        company_repository: CompanyRepository,
        closing_service: ClosingService,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._company_repository = company_repository
        self._closing_service = closing_service

    def close(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        income_statement: IncomeStatement,
        ledger: Ledger,
        chart_of_accounts: ChartOfAccountsTemplate,
        closing_date: date,
    ) -> ClosingResult:
        """Schließt ein Geschäftsjahr atomar ab."""

        try:
            result = self._closing_service.close(
                income_statement=income_statement,
                ledger=ledger,
                chart_of_accounts=chart_of_accounts,
                closing_date=closing_date,
            )

            for booking in result.bookings:
                self._booking_repository.add(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    booking=booking,
                    commit=False,
                )

            self._company_repository.close_fiscal_year(
                company_id,
                fiscal_year,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

        return result

