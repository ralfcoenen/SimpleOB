
"""Workflow für den persistenten Jahresabschluss."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.money import ZERO
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.posting_service import PostingService


class FiscalYearClosingWorkflow:
    """Koordiniert den persistenten Abschluss eines Geschäftsjahres."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        company_repository: CompanyRepository,
        closing_service: ClosingService,
        posting_service: PostingService | None = None,
        statement_builder: FinancialStatementBuilder | None = None,
        income_statement_position: FinancialStatementPosition | None = None,
        account_types: dict[str, AccountType] | None = None,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._company_repository = company_repository
        self._closing_service = closing_service

        dependencies = (
            posting_service,
            statement_builder,
            income_statement_position,
            account_types,
        )

        if any(value is not None for value in dependencies):
            if not all(value is not None for value in dependencies):
                raise ValueError(
                    "Die Abhängigkeiten für die transaktionale "
                    "Abschlussberechnung müssen vollständig "
                    "angegeben werden."
                )

        self._posting_service = posting_service
        self._statement_builder = statement_builder
        self._income_statement_position = income_statement_position
        self._account_types = account_types

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
            self._company_repository.lock_open_fiscal_year(
                company_id,
                fiscal_year,
            )

            if self._statement_builder is not None:
                ledger, income_statement = (
                    self._recalculate_from_database(
                        company_id=company_id,
                        fiscal_year=fiscal_year,
                    )
                )
            elif self._session.get_bind().dialect.name == "postgresql":
                raise RuntimeError(
                    "Für einen PostgreSQL-Jahresabschluss ist "
                    "die transaktionale Neuberechnung erforderlich."
                )

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

    def _recalculate_from_database(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> tuple[Ledger, IncomeStatement]:
        """Berechnet Ledger und GuV aus dem gesperrten Datenstand."""

        assert self._posting_service is not None
        assert self._statement_builder is not None
        assert self._income_statement_position is not None
        assert self._account_types is not None

        bookings = self._booking_repository.list_for_fiscal_year(
            company_id=company_id,
            fiscal_year=fiscal_year,
        )

        ledger = Ledger()

        for booking in bookings:
            if booking.booking_type is BookingType.CLOSING:
                raise ValueError(
                    "Das Geschäftsjahr enthält bereits "
                    "Abschlussbuchungen."
                )

            self._posting_service.post_booking(
                booking=booking,
                ledger=ledger,
            )

        income_statement_balances = tuple(
            balance
            for balance in ledger.balances()
            if self._account_types.get(balance.account_number)
            in (AccountType.REVENUE, AccountType.EXPENSE)
            and (
                balance.debit_balance > ZERO
                or balance.credit_balance > ZERO
            )
        )

        amounts = self._statement_builder.build(
            balances=income_statement_balances,
            root_positions=(self._income_statement_position,),
        )

        income_statement = IncomeStatement(
            income_statement=self._income_statement_position,
            amounts=amounts,
        )

        return ledger, income_statement
