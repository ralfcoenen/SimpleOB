"""Anwendungszustand eines geöffneten Geschäftsjahres."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.trial_balance import TrialBalance
from openbilanz.core.context import ApplicationContext
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.database.vat_booking_detail_repository import (
    VatBookingDetailRepository,
)
from openbilanz.database.vat_configuration_repository import (
    VatConfigurationRepository,
)
from openbilanz.database.vat_input_timing_repository import (
    VatInputTimingRepository,
)
from openbilanz.database.vat_revenue_repository import (
    VatRevenueRepository,
)
from openbilanz.domain.account import Account
from openbilanz.domain.account_mapping_rule import (
    AccountMappingRule,
)
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
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
from openbilanz.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from openbilanz.domain.journal import Journal
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.vat_booking_detail import VatBookingDetail
from openbilanz.domain.vat_configuration import (
    VatConfiguration,
)
from openbilanz.domain.vat_input_timing import VatInputTiming
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue_kind import VatRevenueKind
from openbilanz.reporting.account_activity_report import (
    AccountActivityReport,
)
from openbilanz.reporting.fixed_asset_report import (
    FixedAssetReport,
)
from openbilanz.reporting.journal_report import JournalReport
from openbilanz.reporting.trial_balance_report import (
    TrialBalanceReport,
)
from openbilanz.reporting.vat_advance_return import (
    VatAdvanceReturn,
)
from openbilanz.reporting.vat_report import VatReport
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
from openbilanz.services.fixed_asset_disposal_workflow import (
    FixedAssetDisposalWorkflow,
)
from openbilanz.services.fixed_asset_loss_workflow import (
    FixedAssetLossWorkflow,
)
from openbilanz.services.fixed_asset_reporting_service import (
    FixedAssetReportingService,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetScheduleService,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.services.reporting_service import ReportingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
    TaxonomyStatus,
)
from openbilanz.services.vat_advance_return_timing_service import (
    VatAdvanceReturnTimingService,
)
from openbilanz.services.vat_revenue_posting_workflow import (
    VatRevenuePostingWorkflow,
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
        vat_configuration: VatConfiguration,
        booking_repository: BookingRepository,
        vat_booking_detail_repository: VatBookingDetailRepository | None = None,
        vat_revenue_repository: VatRevenueRepository | None = None,
        company_repository: CompanyRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository | None = None,
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
        fixed_asset_movement_repository: (
            FixedAssetMovementRepository | None
        ) = None,
        fixed_asset_reporting_service: (
            FixedAssetReportingService | None
        ) = None,
        fixed_asset_schedule_service: FixedAssetScheduleService,
        fixed_asset_loss_workflow: (
            FixedAssetLossWorkflow | None
        ) = None,
        fixed_asset_disposal_workflow: (
            FixedAssetDisposalWorkflow | None
        ) = None,
        vat_revenue_posting_workflow: (
            VatRevenuePostingWorkflow | None
        ) = None,
        vat_configuration_repository: (
            VatConfigurationRepository | None
        ) = None,
        vat_input_timing_repository: VatInputTimingRepository | None = None,
    ) -> None:
        self._context = context
        self._vat_configuration = vat_configuration
        self._booking_repository = booking_repository
        self._vat_booking_detail_repository = (
            vat_booking_detail_repository
        )
        self._vat_revenue_repository = (
            vat_revenue_repository
        )
        self._company_repository = company_repository
        self._chart_of_accounts_repository = (
            chart_of_accounts_repository
        )
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
        self._fixed_asset_movement_repository = (
            fixed_asset_movement_repository
        )
        self._fixed_asset_loss_workflow = (
            fixed_asset_loss_workflow
        )
        self._fixed_asset_disposal_workflow = (
            fixed_asset_disposal_workflow
        )
        self._fixed_asset_reporting_service = (
            fixed_asset_reporting_service
        )
        self._fixed_asset_schedule_service = (
            fixed_asset_schedule_service
        )
        self._vat_revenue_posting_workflow = (
            vat_revenue_posting_workflow
        )
        self._vat_configuration_repository = (
            vat_configuration_repository
        )
        self._vat_input_timing_repository = (
            vat_input_timing_repository
        )

        self.reload()

    @property
    def context(self) -> ApplicationContext:
        """Liefert den aktuellen Anwendungskontext."""

        return self._context

    @property
    def vat_configuration(
        self,
    ) -> VatConfiguration:
        """Liefert die umsatzsteuerliche Mandantenkonfiguration."""

        return self._vat_configuration

    def add_account(
        self,
        *,
        account: Account,
        mapping_rule: AccountMappingRule | None,
    ) -> None:
        """Fügt dem Mandantenkontenrahmen ein Konto hinzu."""

        if self._chart_of_accounts_repository is None:
            raise RuntimeError(
                "Die Kontenrahmenverwaltung ist nicht konfiguriert."
            )

        self._chart_of_accounts_repository.add_account(
            company_id=self._context.company.company_id,
            account=account,
            mapping_rule=mapping_rule,
        )

    def update_account(
        self,
        *,
        account: Account,
        mapping_rule: AccountMappingRule | None,
    ) -> None:
        """Aktualisiert ein Konto des Mandantenkontenrahmens."""

        if self._chart_of_accounts_repository is None:
            raise RuntimeError(
                "Die Kontenrahmenverwaltung ist nicht konfiguriert."
            )

        self._chart_of_accounts_repository.update_account(
            company_id=self._context.company.company_id,
            account=account,
            mapping_rule=mapping_rule,
        )


    def update_account_configuration(
        self,
        *,
        control_accounts: AccountingControlAccounts,
        vat_accounts: VatAccounts,
    ) -> None:
        """Aktualisiert die technischen Konten des Mandanten."""

        if self._chart_of_accounts_repository is None:
            raise RuntimeError(
                "Die Kontenrahmenverwaltung ist nicht konfiguriert."
            )

        company_id = self._context.company.company_id

        self._chart_of_accounts_repository.save_account_configuration(
            company_id=company_id,
            control_accounts=control_accounts,
            vat_accounts=vat_accounts,
        )


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

    def post_vat_booking(
        self,
        *,
        booking: Booking,
        booking_details: tuple[VatBookingDetail, ...],
    ) -> None:
        """Verbucht USt-Buchung und USt-Details atomar."""

        if self._vat_revenue_posting_workflow is None:
            raise RuntimeError(
                "Der Umsatzsteuer-Buchungsworkflow "
                "ist nicht konfiguriert."
            )

        self._vat_revenue_posting_workflow.post_booking(
            company=self._context.company,
            fiscal_year=self._context.fiscal_year,
            booking=booking,
            booking_details=booking_details,
        )

        self.reload()

    def post_vat_input_booking(
        self,
        *,
        booking: Booking,
        booking_details: tuple[VatBookingDetail, ...],
        service_date: date,
        invoice_received_date: date,
    ) -> None:
        """Verbucht eine Eingangsrechnung mit Vorsteuer-Zeitzuordnung."""

        if self._vat_revenue_posting_workflow is None:
            raise RuntimeError(
                "Der Umsatzsteuer-Buchungsworkflow "
                "ist nicht konfiguriert."
            )

        timing = VatInputTiming(
            booking_id=booking.booking_id,
            service_date=service_date,
            invoice_received_date=invoice_received_date,
        )

        self._vat_revenue_posting_workflow.post_booking(
            company=self._context.company,
            fiscal_year=self._context.fiscal_year,
            booking=booking,
            booking_details=booking_details,
            input_timing=timing,
        )

        self.reload()

    def post_vat_revenue_booking(
        self,
        *,
        booking: Booking,
        booking_details: tuple[VatBookingDetail, ...],
        gross_amount: Decimal,
        revenue_kind: VatRevenueKind,
        payment_kind: VatPaymentKind,
        service_date: date,
    ) -> None:
        """Verbucht Ausgangsbuchung und USt-Umsatz atomar."""

        if self._vat_revenue_posting_workflow is None:
            raise RuntimeError(
                "Der Umsatzsteuer-Ausgangsworkflow "
                "ist nicht konfiguriert."
            )

        self._vat_revenue_posting_workflow.post(
            company=self._context.company,
            fiscal_year=self._context.fiscal_year,
            booking=booking,
            booking_details=booking_details,
            gross_amount=gross_amount,
            revenue_kind=revenue_kind,
            payment_kind=payment_kind,
            service_date=service_date,
        )

        self.reload()

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

    def build_vat_advance_return(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> VatAdvanceReturn:
        """Erzeugt die Umsatzsteuer-Voranmeldung."""

        if self._vat_booking_detail_repository is None:
            raise RuntimeError(
                "Das USt-Detail-Repository ist nicht konfiguriert."
            )

        if self._vat_revenue_repository is None:
            raise RuntimeError(
                "Das USt-Umsatz-Repository ist nicht konfiguriert."
            )

        if self._vat_input_timing_repository is None:
            raise RuntimeError(
                "Das Vorsteuer-Zeit-Repository ist nicht konfiguriert."
            )

        timing_service = VatAdvanceReturnTimingService(
            booking_repository=self._booking_repository,
            vat_booking_detail_repository=(
                self._vat_booking_detail_repository
            ),
            vat_revenue_repository=(
                self._vat_revenue_repository
            ),
            vat_input_timing_repository=(
                self._vat_input_timing_repository
            ),
        )

        details = timing_service.details_for_period(
            company_id=self._context.company.company_id,
            taxation_method=(
                self._vat_configuration.taxation_method
            ),
            start_date=start_date,
            end_date=end_date,
        )

        return self._reporting_service.vat_advance_return(
            details=details,
            start_date=start_date,
            end_date=end_date,
        )

    def build_vat_report(
        self,
        *,
        start_date: date,
        end_date: date,
        vat_accounts: VatAccounts,
    ) -> VatReport:
        """Erzeugt die Umsatzsteuer-Auswertung."""

        return self._reporting_service.vat_report(
            journal=self._journal,
            start_date=start_date,
            end_date=end_date,
            vat_accounts=vat_accounts,
        )

    def build_fixed_asset_report(
        self,
    ) -> FixedAssetReport:
        """Erzeugt den Anlagenbericht des geöffneten Geschäftsjahres."""

        if self._fixed_asset_reporting_service is None:
            raise RuntimeError(
                "Die Anlagenberichterstattung ist nicht konfiguriert."
            )

        return (
            self._fixed_asset_reporting_service.report_for_company(
                company_id=(
                    self._context.company.company_id
                ),
                start_date=(
                    self._context.fiscal_year.start_date
                ),
                end_date=(
                    self._context.fiscal_year.end_date
                ),
            )
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

    def has_fixed_asset_acquisition(
        self,
        fixed_asset_id: UUID,
    ) -> bool:
        """Prüft, ob eine Anschaffungsbuchung zugeordnet ist."""

        if self._fixed_asset_movement_repository is None:
            raise RuntimeError(
                "Anlagenbewegungen sind nicht konfiguriert."
            )

        movements = (
            self._fixed_asset_movement_repository
            .list_for_fixed_asset(
                fixed_asset_id
            )
        )

        return any(
            movement.movement_type
            is FixedAssetMovementType.ACQUISITION
            for movement in movements
        )

    def update_fixed_asset(
        self,
        fixed_asset: FixedAsset,
    ) -> None:
        """Aktualisiert ein noch änderbares Anlagegut."""

        if not self.is_open:
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if self._fixed_asset_repository is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        if self._fixed_asset_depreciation_repository is None:
            raise RuntimeError(
                "Die Anlagenabschreibungen sind nicht konfiguriert."
            )

        if self._fixed_asset_movement_repository is None:
            raise RuntimeError(
                "Anlagenbewegungen sind nicht konfiguriert."
            )

        existing = self._fixed_asset_repository.get(
            fixed_asset.fixed_asset_id
        )

        if existing is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        if (
            existing.company_id
            != self._context.company.company_id
            or fixed_asset.company_id
            != self._context.company.company_id
        ):
            raise ValueError(
                "Das Anlagegut gehört nicht zum "
                "geöffneten Unternehmen."
            )

        if existing.status is not FixedAssetStatus.ACTIVE:
            raise ValueError(
                "Ein abgegangenes Anlagegut kann nicht "
                "mehr bearbeitet werden."
            )

        depreciations = (
            self._fixed_asset_depreciation_repository
            .list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        if depreciations:
            raise ValueError(
                "Das Anlagegut kann nach der ersten "
                "gebuchten Abschreibung nicht mehr "
                "bearbeitet werden."
            )

        movements = (
            self._fixed_asset_movement_repository
            .list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        acquisition_linked = any(
            movement.movement_type
            is FixedAssetMovementType.ACQUISITION
            for movement in movements
        )

        if acquisition_linked:
            if (
                fixed_asset.asset_account_number
                != existing.asset_account_number
                or fixed_asset.acquisition_cost
                != existing.acquisition_cost
                or fixed_asset.acquisition_date
                != existing.acquisition_date
            ):
                raise ValueError(
                    "Anlagenkonto, Anschaffungsdatum und "
                    "Anschaffungskosten können nach der "
                    "Zuordnung der Anschaffungsbuchung "
                    "nicht mehr geändert werden."
                )

        self._fixed_asset_repository.update(
            fixed_asset=fixed_asset
        )

    def delete_fixed_asset(
        self,
        fixed_asset_id: UUID,
    ) -> None:
        """Löscht ein noch nicht buchungswirksames Anlagegut."""

        if not self.is_open:
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if self._fixed_asset_repository is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        if self._fixed_asset_depreciation_repository is None:
            raise RuntimeError(
                "Die Anlagenabschreibungen sind nicht konfiguriert."
            )

        if self._fixed_asset_movement_repository is None:
            raise RuntimeError(
                "Anlagenbewegungen sind nicht konfiguriert."
            )

        fixed_asset = self._fixed_asset_repository.get(
            fixed_asset_id
        )

        if fixed_asset is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        if (
            fixed_asset.company_id
            != self._context.company.company_id
        ):
            raise ValueError(
                "Das Anlagegut gehört nicht zum "
                "geöffneten Unternehmen."
            )

        if fixed_asset.status is not FixedAssetStatus.ACTIVE:
            raise ValueError(
                "Ein abgegangenes Anlagegut kann nicht "
                "gelöscht werden."
            )

        depreciations = (
            self._fixed_asset_depreciation_repository
            .list_for_fixed_asset(
                fixed_asset_id
            )
        )

        if depreciations:
            raise ValueError(
                "Das Anlagegut kann nach der ersten "
                "gebuchten Abschreibung nicht mehr "
                "gelöscht werden."
            )

        movements = (
            self._fixed_asset_movement_repository
            .list_for_fixed_asset(
                fixed_asset_id
            )
        )

        if movements:
            raise ValueError(
                "Das Anlagegut kann nach einer "
                "buchungswirksamen Anlagenbewegung "
                "nicht mehr gelöscht werden."
            )

        self._fixed_asset_repository.delete(
            fixed_asset_id=fixed_asset_id
        )

    def link_fixed_asset_acquisition(
        self,
        *,
        fixed_asset_id: UUID,
        booking_id: UUID,
        booking_line_position: int,
    ) -> FixedAssetMovement:
        """Ordnet eine Anschaffungsbuchung einem Anlagegut zu."""

        if not self.is_open:
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if self._fixed_asset_repository is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        if self._fixed_asset_movement_repository is None:
            raise RuntimeError(
                "Anlagenbewegungen sind nicht konfiguriert."
            )

        if not isinstance(
            fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        if not isinstance(
            booking_id,
            UUID,
        ):
            raise TypeError(
                "booking_id must be a UUID"
            )

        if not isinstance(
            booking_line_position,
            int,
        ):
            raise TypeError(
                "booking_line_position must be an int"
            )

        if booking_line_position < 0:
            raise ValueError(
                "booking_line_position must not be negative"
            )

        fixed_asset = (
            self._fixed_asset_repository.get(
                fixed_asset_id
            )
        )

        if fixed_asset is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        if (
            fixed_asset.company_id
            != self._context.company.company_id
        ):
            raise ValueError(
                "Das Anlagegut gehört nicht zum "
                "geöffneten Unternehmen."
            )

        booking = self._booking_repository.get(
            booking_id
        )

        if booking is None:
            raise ValueError(
                "Die Buchung ist nicht vorhanden."
            )

        if not self._context.fiscal_year.contains(
            booking.booking_date
        ):
            raise ValueError(
                "Die Buchung gehört nicht zum "
                "geöffneten Geschäftsjahr."
            )

        if (
            booking_line_position
            >= len(booking.lines)
        ):
            raise ValueError(
                "Die Buchungszeile ist nicht vorhanden."
            )

        booking_line = booking.lines[
            booking_line_position
        ]

        if (
            booking_line.account_number
            != fixed_asset.asset_account_number
        ):
            raise ValueError(
                "Die Buchungszeile gehört nicht zum "
                "Anlagenkonto des Anlageguts."
            )

        if (
            booking_line.amount
            != fixed_asset.acquisition_cost
        ):
            raise ValueError(
                "Der Betrag der Buchungszeile stimmt "
                "nicht mit den Anschaffungskosten "
                "des Anlageguts überein."
            )

        existing_movements = (
            self._fixed_asset_movement_repository
            .list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        if any(
            movement.movement_type
            is FixedAssetMovementType.ACQUISITION
            for movement in existing_movements
        ):
            raise ValueError(
                "Dem Anlagegut ist bereits eine "
                "Anschaffungsbuchung zugeordnet."
            )

        movement = FixedAssetMovement(
            fixed_asset_id=(
                fixed_asset.fixed_asset_id
            ),
            fiscal_year_end=(
                self._context.fiscal_year.end_date
            ),
            movement_date=booking.booking_date,
            amount=booking_line.amount,
            booking_id=booking.booking_id,
            movement_type=(
                FixedAssetMovementType.ACQUISITION
            ),
        )

        self._fixed_asset_movement_repository.add(
            movement=movement,
            booking_line_position=booking_line_position,
        )

        return movement

    def pending_fixed_asset_loss_depreciation(
        self,
        *,
        fixed_asset_id: UUID,
        loss_date: date,
    ) -> DepreciationProposal | None:
        """Ermittelt eine noch erforderliche AfA vor Totalverlust."""

        if self._fixed_asset_loss_workflow is None:
            raise RuntimeError(
                "Der Workflow für Anlagenverluste "
                "ist nicht konfiguriert."
            )

        return (
            self._fixed_asset_loss_workflow
            .pending_depreciation(
                fixed_asset_id=fixed_asset_id,
                fiscal_year=self._context.fiscal_year,
                loss_date=loss_date,
            )
        )

    def pending_fixed_asset_disposal_depreciation(
        self,
        *,
        fixed_asset_id: UUID,
        disposal_date: date,
    ) -> DepreciationProposal | None:
        """Ermittelt eine noch erforderliche AfA vor Anlagenverkauf."""

        if self._fixed_asset_disposal_workflow is None:
            raise RuntimeError(
                "Der Workflow für Anlagenverkäufe "
                "ist nicht konfiguriert."
            )

        return (
            self._fixed_asset_disposal_workflow
            .pending_depreciation(
                fixed_asset_id=fixed_asset_id,
                fiscal_year=self._context.fiscal_year,
                disposal_date=disposal_date,
            )
        )

    def confirm_fixed_asset_disposal(
        self,
        *,
        fixed_asset_id: UUID,
        disposal_date: date,
        net_sale_amount: Decimal,
        settlement_account_number: str,
        revenue_account_number: str,
        output_tax_account_number: str,
        book_value_expense_account_number: str,
        tax_rate: Decimal = Decimal("0.19"),
    ) -> FixedAssetMovement:
        """Bucht den Verkauf eines Anlageguts."""

        if not self.is_open:
            raise RuntimeError(
                "Das Geschäftsjahr ist bereits abgeschlossen."
            )

        if self._fixed_asset_disposal_workflow is None:
            raise RuntimeError(
                "Der Workflow für Anlagenverkäufe "
                "ist nicht konfiguriert."
            )

        movement = (
            self._fixed_asset_disposal_workflow
            .confirm_disposal(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                fixed_asset_id=fixed_asset_id,
                disposal_date=disposal_date,
                net_sale_amount=net_sale_amount,
                settlement_account_number=(
                    settlement_account_number
                ),
                revenue_account_number=(
                    revenue_account_number
                ),
                output_tax_account_number=(
                    output_tax_account_number
                ),
                book_value_expense_account_number=(
                    book_value_expense_account_number
                ),
                tax_rate=tax_rate,
            )
        )

        self.reload()

        return movement

    def confirm_fixed_asset_loss(
        self,
        *,
        fixed_asset_id: UUID,
        loss_date: date,
        loss_expense_account_number: str,
    ) -> FixedAssetMovement:
        """Bucht den vollständigen Verlust eines Anlageguts."""

        if not self.is_open:
            raise RuntimeError(
                "Das Geschäftsjahr ist bereits abgeschlossen."
            )

        if self._fixed_asset_loss_workflow is None:
            raise RuntimeError(
                "Der Workflow für Anlagenverluste "
                "ist nicht konfiguriert."
            )

        movement = (
            self._fixed_asset_loss_workflow.confirm_loss(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                fixed_asset_id=fixed_asset_id,
                loss_date=loss_date,
                loss_expense_account_number=(
                    loss_expense_account_number
                ),
            )
        )

        self.reload()

        return movement

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
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if self._fixed_asset_repository is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        if self._fixed_asset_depreciation_workflow is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        fixed_asset = self._fixed_asset_repository.get(
            proposal.fixed_asset_id
        )

        if fixed_asset is None:
            raise ValueError(
                "Das Anlagegut wurde nicht gefunden."
            )

        depreciation = (
            self._fixed_asset_depreciation_workflow.confirm(
                company_id=(
                    self._context.company.company_id
                ),
                fiscal_year=(
                    self._context.fiscal_year
                ),
                proposal=proposal,
                asset_code=fixed_asset.asset_code,
            )
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

        fixed_asset_schedule = (
            self._fixed_asset_schedule_service
            .schedule_for_company(
                company_id=self._context.company.company_id,
                start_date=self._context.fiscal_year.start_date,
                end_date=self._context.fiscal_year.end_date,
            )
        )

        document = self._e_bilanz_service.build(
            master_data=master_data,
            fiscal_year=self._context.fiscal_year,
            amounts=preparation.amounts,
            entity_identifier=entity.value,
            entity_scheme=entity.scheme,
            previous_fiscal_year=(self.managed_fiscal_year.opening_source),
            account_details=account_details,
            fixed_asset_schedule=fixed_asset_schedule,
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

    def save_vat_configuration(
        self,
        configuration: VatConfiguration,
    ) -> None:
        """Speichert die umsatzsteuerliche Mandantenkonfiguration."""

        if self._vat_configuration_repository is None:
            raise RuntimeError(
                "Die Umsatzsteuerkonfiguration ist nicht konfiguriert."
            )

        self._vat_configuration_repository.save(
            company_id=self._context.company.company_id,
            configuration=configuration,
        )

        self._vat_configuration = configuration
