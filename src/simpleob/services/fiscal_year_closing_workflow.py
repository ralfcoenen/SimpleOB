
"""Workflow für den persistenten Jahresabschluss."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.balance_sheet_presentation import (
    BalanceSheetPresentation,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_type import BookingType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.services.closing_result import ClosingResult
from simpleob.services.closing_service import ClosingService
from simpleob.services.posting_service import PostingService
from simpleob.services.vat_reconciliation_service import (
    VatReconciliationProposal,
    VatReconciliationService,
)


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
        vat_reconciliation_service: VatReconciliationService | None = None,
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
        self._vat_reconciliation_service = (
            vat_reconciliation_service or VatReconciliationService()
        )

    def update_accounting_context(
        self,
        *,
        closing_service: ClosingService,
        statement_builder: FinancialStatementBuilder,
        income_statement_position: FinancialStatementPosition,
        account_types: dict[str, AccountType],
    ) -> None:
        """Übernimmt einen neu geladenen Kontenrahmenkontext."""

        self._closing_service = closing_service
        self._statement_builder = statement_builder
        self._income_statement_position = income_statement_position
        self._account_types = account_types

    def post_vat_reconciliation(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        confirmed_proposal: VatReconciliationProposal,
        confirmed: bool,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> tuple[Booking, ...]:
        """Speichert einen bestätigten Vorschlag nach gesperrter Neuberechnung."""

        if confirmed is not True:
            raise ValueError(
                "Die Umsatzsteuerverrechnung wurde nicht ausdrücklich "
                "bestätigt."
            )
        if self._posting_service is None:
            raise RuntimeError(
                "Für die Umsatzsteuerverrechnung ist die transaktionale "
                "Hauptbuch-Neuberechnung nicht konfiguriert."
            )

        try:
            self._company_repository.lock_open_fiscal_year(
                company_id,
                fiscal_year,
            )
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

            current_proposal = (
                self._vat_reconciliation_service.build_proposal(
                    bookings=bookings,
                    ledger=ledger,
                    fiscal_year=fiscal_year,
                    vat_accounts=vat_accounts,
                    account_roles=account_roles,
                    chart_of_accounts=chart_of_accounts,
                )
            )
            if current_proposal.snapshot != confirmed_proposal.snapshot:
                raise ValueError(
                    "Der Buchungsstand hat sich seit der Vorschau geändert. "
                    "Bitte erstellen und prüfen Sie einen neuen Vorschlag."
                )

            if not current_proposal.bookings:
                self._session.commit()
                return ()

            for booking in current_proposal.bookings:
                self._booking_repository.add(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    booking=booking,
                    commit=False,
                )
            self._session.commit()
            return current_proposal.bookings
        except Exception:
            self._session.rollback()
            raise

    def close(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        income_statement: IncomeStatement,
        ledger: Ledger,
        chart_of_accounts: ChartOfAccountsTemplate,
        closing_date: date,
        balance_sheet_presentation: BalanceSheetPresentation = (
            BalanceSheetPresentation.BEFORE_APPROPRIATION
        ),
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

            if self._statement_builder is not None:
                self._statement_builder.ensure_person_account_balances_supported(
                    ledger.balances()
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
                balance_sheet_presentation=(
                    balance_sheet_presentation
                ),
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
