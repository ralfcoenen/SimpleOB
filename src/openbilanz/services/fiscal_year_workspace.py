"""Anwendungszustand eines geöffneten Geschäftsjahres."""

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.trial_balance import TrialBalance
from openbilanz.core.context import ApplicationContext
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.journal import Journal
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationResult,
    EBilanzPreparationService,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.taxonomy.arelle_adapter import (
    ArelleValidationResult,
)
from openbilanz.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)
from openbilanz.taxonomy.entity_identifier import (
    EntityIdentifier,
)


class FiscalYearWorkspace:
    """Koordiniert den Zustand eines geöffneten Geschäftsjahres."""

    def __init__(
        self,
        *,
        context: ApplicationContext,
        booking_repository: BookingRepository,
        company_repository: CompanyRepository,
        posting_service: PostingService,
        closing_workflow: FiscalYearClosingWorkflow,
        closing_consistency_service: ClosingConsistencyService,
        e_bilanz_preparation_service: EBilanzPreparationService,
        e_bilanz_service: EBilanzService,
        
    ) -> None:
        self._context = context
        self._booking_repository = booking_repository
        self._company_repository = company_repository
        self._posting_service = posting_service
        self._closing_workflow = closing_workflow
        self._closing_consistency_service = (
            closing_consistency_service
        )

        self._journal = Journal()
        self._ledger = Ledger()
        self._pre_closing_ledger = Ledger()
        self._e_bilanz_preparation_service = (
            e_bilanz_preparation_service
        )
        self._e_bilanz_service = e_bilanz_service

        self.reload()

    @property
    def context(self) -> ApplicationContext:
        """Liefert den aktuellen Anwendungskontext."""

        return self._context

    @property
    def journal(self) -> Journal:
        """Liefert das rekonstruierte Journal."""

        return self._journal

    @property
    def ledger(self) -> Ledger:
        """Liefert das rekonstruierte Hauptbuch."""

        return self._ledger

    @property
    def pre_closing_ledger(self) -> Ledger:
        """Liefert das Hauptbuch ohne Jahresabschlussbuchungen."""

        return self._pre_closing_ledger
    
    @property
    def managed_fiscal_year(self) -> ManagedFiscalYear:
        """Liefert das Geschäftsjahr einschließlich Verwaltungsstatus."""

        fiscal_years = (
            self._company_repository.get_managed_fiscal_years(
                self._context.company.company_id
            )
        )

        for managed_fiscal_year in fiscal_years:
            if (
                managed_fiscal_year.fiscal_year
                == self._context.fiscal_year
            ):
                return managed_fiscal_year

        raise ValueError(
            "Das geöffnete Geschäftsjahr wurde nicht gefunden."
        )

    @property
    def is_open(self) -> bool:
        """Gibt an, ob noch Buchungen zulässig sind."""

        return (
            self.managed_fiscal_year.status
            is FiscalYearStatus.OPEN
        )

    @property
    def is_closed(self) -> bool:
        """Gibt an, ob das Geschäftsjahr abgeschlossen ist."""

        return (
            self.managed_fiscal_year.status
            is FiscalYearStatus.CLOSED
        )

    def post_booking(
        self,
        booking: Booking,
    ) -> None:
        """Verbucht und persistiert eine laufende Buchung."""

        self._booking_repository.add(
            company_id=self._context.company.company_id,
            fiscal_year=self._context.fiscal_year,
            booking=booking,
        )

        self.reload()


    def validate_closing(
        self,
        *,
        balance_sheet: BalanceSheet,
        income_statement: IncomeStatement,
        closing_result: ClosingResult,
        balances: tuple[AccountBalance, ...],
        mapper: AccountMapper,
    ) -> ClosingConsistencyResult:
        """Prüft den aktuellen Jahresabschluss auf Konsistenz."""

        trial_balance = TrialBalance(
            self._ledger
        )

        return self._closing_consistency_service.validate(
            trial_balance=trial_balance,
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            closing_result=closing_result,
            balances=balances,
            mapper=mapper,
        )
    
    def close_fiscal_year(
        self,
        *,
        income_statement: IncomeStatement,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> ClosingResult:
        """Schließt das aktuelle Geschäftsjahr persistent ab."""

        result = self._closing_workflow.close(
            company_id=self._context.company.company_id,
            fiscal_year=self._context.fiscal_year,
            income_statement=income_statement,
            ledger=self._ledger,
            chart_of_accounts=chart_of_accounts,
            closing_date=self._context.fiscal_year.end_date,
        )

        self.reload()

        return result

    def reload(self) -> None:
        """Rekonstruiert Journal und Ledger aus der Datenbank."""

        journal = Journal()
        ledger = Ledger()
        pre_closing_ledger = Ledger()

        bookings = (
            self._booking_repository.list_for_fiscal_year(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
            )
        )

        for booking in bookings:
            self._posting_service.post_booking(
                booking=booking,
                ledger=ledger,
                journal=journal,
            )

            if booking.booking_type is not BookingType.CLOSING:
                self._posting_service.post_booking(
                    booking=booking,
                    ledger=pre_closing_ledger,
                )

        self._journal = journal
        self._ledger = ledger
        self._pre_closing_ledger = pre_closing_ledger
    
    def load_company_master_data(
        self,
    ) -> CompanyMasterData:
        """Lädt die Stammdaten des geöffneten Unternehmens."""

        master_data = (
            self._company_repository.get_master_data(
                self._context.company.company_id
            )
        )

        if master_data is None:
            raise ValueError(
                "Unternehmen wurde nicht gefunden."
            )

        return master_data


    def save_company_master_data(
        self,
        master_data: CompanyMasterData,
    ) -> None:
        """Speichert die Stammdaten des geöffneten Unternehmens."""

        if (
            master_data.company
            != self._context.company
        ):
            raise ValueError(
                "Die Stammdaten gehören nicht zum "
                "geöffneten Unternehmen."
            )

        self._company_repository.save_master_data(
            master_data
        )
    
    def prepare_e_bilanz(
        self,
        *,
        income_statement: IncomeStatement,
    ) -> EBilanzPreparationResult:
        """Bereitet die HGB-Werte des abgeschlossenen Geschäftsjahres auf."""

        if not self.is_closed:
            raise ValueError(
                "Die E-Bilanz kann erst nach dem "
                "Jahresabschluss vorbereitet werden."
            )

        return self._e_bilanz_preparation_service.prepare(
            income_statement=income_statement,
            closed_ledger=self._ledger,
        )
        
    def build_e_bilanz(
        self,
        *,
        preparation: EBilanzPreparationResult,
    ) -> EBilanzDocument:
        """Erzeugt die E-Bilanz des geöffneten Geschäftsjahres."""

        if not self.is_closed:
            raise ValueError(
                "Die E-Bilanz kann erst nach dem "
                "Jahresabschluss erzeugt werden."
            )

        master_data = self.load_company_master_data()
        entity = EntityIdentifier.from_company(
            self._context.company
        )

        return self._e_bilanz_service.build(
            master_data=master_data,
            fiscal_year=self._context.fiscal_year,
            amounts=preparation.amounts,
            entity_identifier=entity.value,
            entity_scheme=entity.scheme,    
            previous_fiscal_year=(
                self.managed_fiscal_year.opening_source
            ),
        )
        
    def validate_e_bilanz(
        self,
        document: EBilanzDocument,
    ) -> ArelleValidationResult:
        """Validiert eine erzeugte E-Bilanz."""

        if not self.is_closed:
            raise ValueError(
                "Die E-Bilanz kann erst nach dem "
                "Jahresabschluss validiert werden."
            )

        return self._e_bilanz_service.validate(
            document,
            fiscal_year=self._context.fiscal_year,
        )