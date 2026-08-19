"""Anwendungszustand eines geöffneten Geschäftsjahres."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.trial_balance import TrialBalance
from openbilanz.core.context import ApplicationContext
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
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
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from openbilanz.domain.journal import Journal
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear
from openbilanz.reporting.account_activity_report import (
    AccountActivityReport,
)
from openbilanz.reporting.journal_report import JournalReport
from openbilanz.reporting.trial_balance_report import (
    TrialBalanceReport,
)
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.depreciation_service import (
    DepreciationService,
)
from openbilanz.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)
from openbilanz.services.e_bilanz_export_service import (
    EBilanzExportService,
)
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationResult,
    EBilanzPreparationService,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.services.reporting_service import ReportingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
    TaxonomyStatus,
)
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
        reporting_service: ReportingService | None = None,
        closing_workflow: FiscalYearClosingWorkflow,
        closing_consistency_service: ClosingConsistencyService,
        e_bilanz_preparation_service: EBilanzPreparationService,
        e_bilanz_service: EBilanzService,
        e_bilanz_account_detail_service: EBilanzAccountDetailService,
        e_bilanz_export_service: EBilanzExportService,
        taxonomy_management_service: TaxonomyManagementService,
        fixed_asset_repository: FixedAssetRepository | None = None,
        fixed_asset_depreciation_repository: (
            FixedAssetDepreciationRepository | None
        ) = None,
        depreciation_service: DepreciationService | None = None,
        fixed_asset_depreciation_workflow: (
            FixedAssetDepreciationWorkflow | None
        ) = None,
    ) -> None:
        self._context = context
        self._booking_repository = booking_repository
        self._company_repository = company_repository
        self._posting_service = posting_service
        self._reporting_service = (
            reporting_service
            if reporting_service is not None
            else ReportingService()
        )
        self._closing_workflow = closing_workflow
        self._closing_consistency_service = closing_consistency_service

        self._journal = Journal()
        self._ledger = Ledger()
        self._pre_closing_ledger = Ledger()
        self._e_bilanz_preparation_service = e_bilanz_preparation_service
        self._e_bilanz_service = e_bilanz_service
        self._e_bilanz_account_detail_service = e_bilanz_account_detail_service
        self._e_bilanz_export_service = e_bilanz_export_service
        self._validated_e_bilanz_document: EBilanzDocument | None = None
        self._taxonomy_management_service = taxonomy_management_service
        self._fixed_asset_repository = fixed_asset_repository
        self._fixed_asset_depreciation_repository = fixed_asset_depreciation_repository
        self._depreciation_service = depreciation_service
        self._fixed_asset_depreciation_workflow = fixed_asset_depreciation_workflow

        self.reload()

    @property
    def context(self) -> ApplicationContext:
        """Liefert den aktuellen Anwendungskontext."""

        return self._context

    @property
    def taxonomy_status(self) -> TaxonomyStatus:
        """Liefert den Taxonomiestatus des geöffneten Geschäftsjahres."""

        return self._taxonomy_management_service.status_for(self._context.fiscal_year)

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

        fiscal_years = self._company_repository.get_managed_fiscal_years(
            self._context.company.company_id
        )

        for managed_fiscal_year in fiscal_years:
            if managed_fiscal_year.fiscal_year == self._context.fiscal_year:
                return managed_fiscal_year

        raise ValueError("Das geöffnete Geschäftsjahr wurde nicht gefunden.")

    @property
    def is_open(self) -> bool:
        """Gibt an, ob noch Buchungen zulässig sind."""

        return self.managed_fiscal_year.status is FiscalYearStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """Gibt an, ob das Geschäftsjahr abgeschlossen ist."""

        return self.managed_fiscal_year.status is FiscalYearStatus.CLOSED

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

    def build_trial_balance_report(
        self,
        *,
        start_date: date,
        end_date: date,
        opening_balance_account_number: str,
    ) -> TrialBalanceReport:
        """Erzeugt die Summen- und Saldenliste."""

        return self._reporting_service.trial_balance_report(
            ledger=self._pre_closing_ledger,
            journal=self._journal,
            start_date=start_date,
            end_date=end_date,
            opening_balance_account_number=(
                opening_balance_account_number
            ),
        )

    def build_account_activity_report(
        self,
        *,
        account_number: str,
        start_date: date,
        end_date: date,
    ) -> AccountActivityReport:
        """Erzeugt eine Kontenauswertung für das geöffnete Geschäftsjahr."""

        return self._reporting_service.account_activity_report(
            journal=self._journal,
            account_number=account_number,
            start_date=start_date,
            end_date=end_date,
        )

    def build_journal_report(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> JournalReport:
        """Erzeugt das Journal für einen Berichtszeitraum."""

        return self._reporting_service.journal_report(
            journal=self._journal,
            start_date=start_date,
            end_date=end_date,
        )

    def install_required_taxonomy(self) -> None:
        """Installiert die benötigte Taxonomie."""

        self._taxonomy_management_service.install_required_taxonomy(
            self._context.fiscal_year
        )

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

        trial_balance = TrialBalance(self._ledger)

        return self._closing_consistency_service.validate(
            trial_balance=trial_balance,
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            closing_result=closing_result,
            balances=balances,
            mapper=mapper,
        )

    def list_fixed_assets(
        self,
    ) -> tuple[FixedAsset, ...]:
        """Lädt die Anlagegüter des geöffneten Unternehmens."""

        if self._fixed_asset_repository is None:
            raise RuntimeError("Die Anlagenbuchhaltung ist nicht konfiguriert.")

        return self._fixed_asset_repository.list_for_company(
            self._context.company.company_id
        )

    def add_fixed_asset(
        self,
        fixed_asset: FixedAsset,
    ) -> None:
        """Speichert ein Anlagegut des geöffneten Unternehmens."""

        if not self.is_open:
            raise ValueError("Das Geschäftsjahr ist abgeschlossen.")

        if self._fixed_asset_repository is None:
            raise RuntimeError("Die Anlagenbuchhaltung ist nicht konfiguriert.")

        if fixed_asset.company_id != self._context.company.company_id:
            raise ValueError("Das Anlagegut gehört nicht zum geöffneten Unternehmen.")

        self._fixed_asset_repository.add(fixed_asset=fixed_asset)

    def build_depreciation_proposals(
        self,
    ) -> tuple[DepreciationProposal, ...]:
        """Ermittelt noch offene lineare AfA-Vorschläge."""

        if not self.is_open:
            raise ValueError("Das Geschäftsjahr ist abgeschlossen.")

        if (
            self._fixed_asset_repository is None
            or self._fixed_asset_depreciation_repository is None
            or self._depreciation_service is None
        ):
            raise RuntimeError("Die Anlagenbuchhaltung ist nicht konfiguriert.")

        assets = self._fixed_asset_repository.list_for_company(
            self._context.company.company_id
        )

        proposals: list[DepreciationProposal] = []

        for asset in assets:
            if asset.status is not FixedAssetStatus.ACTIVE:
                continue

            depreciations = (
                self._fixed_asset_depreciation_repository.list_for_fixed_asset(
                    asset.fixed_asset_id
                )
            )

            already_confirmed = any(
                depreciation.fiscal_year_end == self._context.fiscal_year.end_date
                for depreciation in depreciations
            )

            if already_confirmed:
                continue

            previous_depreciation = sum(
                (depreciation.amount for depreciation in depreciations),
                start=Decimal("0.00"),
            )

            proposal = self._depreciation_service.build_proposal(
                fixed_asset=asset,
                fiscal_year=self._context.fiscal_year,
                previous_depreciation=(previous_depreciation),
                expense_account_number=(asset.depreciation_expense_account_number),
                asset_account_number=(asset.asset_account_number),
            )

            if proposal is not None:
                proposals.append(proposal)

        return tuple(proposals)

    def confirm_depreciation(
        self,
        proposal: DepreciationProposal,
    ) -> FixedAssetDepreciation:
        """Bucht einen bestätigten AfA-Vorschlag."""

        if not self.is_open:
            raise ValueError("Das Geschäftsjahr ist abgeschlossen.")

        if self._fixed_asset_depreciation_workflow is None:
            raise RuntimeError("Die Anlagenbuchhaltung ist nicht konfiguriert.")

        depreciation = self._fixed_asset_depreciation_workflow.confirm(
            company_id=(self._context.company.company_id),
            fiscal_year=(self._context.fiscal_year),
            proposal=proposal,
        )

        self.reload()

        return depreciation

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

        bookings = self._booking_repository.list_for_fiscal_year(
            company_id=self._context.company.company_id,
            fiscal_year=self._context.fiscal_year,
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

        master_data = self._company_repository.get_master_data(
            self._context.company.company_id
        )

        if master_data is None:
            raise ValueError("Unternehmen wurde nicht gefunden.")

        return master_data

    def save_company_master_data(
        self,
        master_data: CompanyMasterData,
    ) -> None:
        """Speichert die Stammdaten des geöffneten Unternehmens."""

        if master_data.company != self._context.company:
            raise ValueError("Die Stammdaten gehören nicht zum geöffneten Unternehmen.")

        self._company_repository.save_master_data(master_data)

    def prepare_e_bilanz(
        self,
        *,
        income_statement: IncomeStatement,
    ) -> EBilanzPreparationResult:
        """Bereitet die HGB-Werte des abgeschlossenen Geschäftsjahres auf."""

        if not self.is_closed:
            raise ValueError(
                "Die E-Bilanz kann erst nach dem Jahresabschluss vorbereitet werden."
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
                "Die E-Bilanz kann erst nach dem Jahresabschluss erzeugt werden."
            )

        master_data = self.load_company_master_data()
        entity = EntityIdentifier.from_company(self._context.company)

        account_details = self._e_bilanz_account_detail_service.build_for_e_bilanz(
            pre_closing_ledger=self._pre_closing_ledger,
            closed_ledger=self._ledger,
        )

        document = self._e_bilanz_service.build(
            master_data=master_data,
            fiscal_year=self._context.fiscal_year,
            amounts=preparation.amounts,
            entity_identifier=entity.value,
            entity_scheme=entity.scheme,
            previous_fiscal_year=(self.managed_fiscal_year.opening_source),
            account_details=account_details,
        )

        self._validated_e_bilanz_document = None

        return document

    def validate_e_bilanz(
        self,
        document: EBilanzDocument,
    ) -> ArelleValidationResult:
        """Validiert eine erzeugte E-Bilanz."""

        if not self.is_closed:
            raise ValueError(
                "Die E-Bilanz kann erst nach dem Jahresabschluss validiert werden."
            )

        result = self._e_bilanz_service.validate(
            document,
            fiscal_year=self._context.fiscal_year,
        )

        if result.is_valid:
            self._validated_e_bilanz_document = document
        elif self._validated_e_bilanz_document is document:
            self._validated_e_bilanz_document = None

        return result

    def export_e_bilanz(
        self,
        *,
        document: EBilanzDocument,
        target: Path,
    ) -> Path:
        """Exportiert eine erfolgreich validierte E-Bilanz."""

        if document is not self._validated_e_bilanz_document:
            raise ValueError(
                "Die E-Bilanz muss vor dem Export erfolgreich validiert werden."
            )

        return self._e_bilanz_export_service.export(
            document=document,
            target=target,
        )
