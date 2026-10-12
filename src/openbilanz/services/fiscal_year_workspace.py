"""Anwendungszustand eines geöffneten Geschäftsjahres."""

from dataclasses import replace
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
from openbilanz.database.equity_contribution_repository import (
    EquityContributionRepository,
)
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.database.profit_appropriation_annual_data_repository import (
    ProfitAppropriationAnnualDataRepository,
)
from openbilanz.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from openbilanz.database.shareholder_repository import (
    ShareholderRepository,
)
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)
from openbilanz.domain.account import Account
from openbilanz.domain.account_mapping_rule import (
    AccountMappingRule,
)
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.bvv_evaluation import BvvEvaluation
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
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.equity_contribution_reference import (
    EquityContributionReference,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)
from openbilanz.domain.fixed_asset_disposal_detail import (
    FixedAssetDisposalDetail,
)
from openbilanz.domain.fixed_asset_disposal_preview import (
    FixedAssetDisposalPreview,
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
from openbilanz.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from openbilanz.domain.profit_appropriation_posting import (
    ProfitAppropriationPosting,
)
from openbilanz.domain.profit_appropriation_posting_proposal import (
    ProfitAppropriationPostingProposal,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)
from openbilanz.domain.shareholder import Shareholder
from openbilanz.domain.tax_depreciation_adjustment import (
    TaxDepreciationAdjustment,
)
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.eric.bilanz_generation.bvv_value_builder import (
    BvvValueBuilder,
)
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
from openbilanz.services.fixed_asset_disposal_service import (
    FixedAssetDisposalService,
)
from openbilanz.services.fixed_asset_disposal_workflow import (
    FixedAssetDisposalWorkflow,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetScheduleService,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.services.profit_appropriation_posting_service import (
    ProfitAppropriationPostingService,
)
from openbilanz.services.profit_appropriation_posting_workflow import (
    ProfitAppropriationPostingWorkflow,
)
from openbilanz.services.profit_appropriation_service import (
    ProfitAppropriationService,
)
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
        profit_appropriation_annual_data_repository: (
            ProfitAppropriationAnnualDataRepository | None
        ) = None,
        profit_appropriation_service: (
            ProfitAppropriationService | None
        ) = None,
        profit_appropriation_posting_repository: (
            ProfitAppropriationPostingRepository | None
        ) = None,
        equity_contribution_repository: (
            EquityContributionRepository | None
        ) = None,
        profit_appropriation_posting_service: (
            ProfitAppropriationPostingService | None
        ) = None,
        profit_appropriation_posting_workflow: (
            ProfitAppropriationPostingWorkflow | None
        ) = None,
        shareholder_repository: ShareholderRepository | None = None,
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
        tax_depreciation_adjustment_repository: (
            TaxDepreciationAdjustmentRepository | None
        ) = None,
        depreciation_service: DepreciationService | None = None,
        fixed_asset_depreciation_workflow: (
            FixedAssetDepreciationWorkflow | None
        ) = None,
        fixed_asset_movement_repository: (
            FixedAssetMovementRepository | None
        ) = None,
        fixed_asset_schedule_service: (
            FixedAssetScheduleService | None
        ) = None,
        fixed_asset_disposal_service: (
            FixedAssetDisposalService | None
        ) = None,
        fixed_asset_disposal_workflow: (
            FixedAssetDisposalWorkflow | None
        ) = None,
    ) -> None:
        self._context = context
        self._booking_repository = booking_repository
        self._company_repository = company_repository
        self._profit_appropriation_annual_data_repository = (
            profit_appropriation_annual_data_repository
        )
        self._profit_appropriation_service = (
            profit_appropriation_service
            if profit_appropriation_service is not None
            else ProfitAppropriationService()
        )
        self._profit_appropriation_posting_repository = (
            profit_appropriation_posting_repository
        )
        self._equity_contribution_repository = (
            equity_contribution_repository
        )
        self._profit_appropriation_posting_service = (
            profit_appropriation_posting_service
            if profit_appropriation_posting_service is not None
            else ProfitAppropriationPostingService()
        )
        self._profit_appropriation_posting_workflow = (
            profit_appropriation_posting_workflow
        )
        self._shareholder_repository = (
            shareholder_repository
        )
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
        self._fixed_asset_schedule_service = (
            fixed_asset_schedule_service
        )
        self._fixed_asset_disposal_service = (
            fixed_asset_disposal_service
            if fixed_asset_disposal_service is not None
            else FixedAssetDisposalService()
        )
        self._fixed_asset_disposal_workflow = (
            fixed_asset_disposal_workflow
        )
        self._tax_depreciation_adjustment_repository = (
            tax_depreciation_adjustment_repository
        )

        self.reload()

    @property
    def context(self) -> ApplicationContext:
        """Liefert den aktuellen Anwendungskontext."""

        return self._context

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


    def load_account_configuration(
        self,
    ) -> tuple[
        AccountingControlAccounts,
        VatAccounts,
        AccountingAccountRoles,
    ]:
        """Lädt die Kontenkonfiguration des geöffneten Mandanten."""

        if self._chart_of_accounts_repository is None:
            raise RuntimeError(
                "Die Kontenrahmenverwaltung ist nicht konfiguriert."
            )

        company_id = self._context.company.company_id

        control_accounts = (
            self._chart_of_accounts_repository
            .load_control_accounts(company_id)
        )
        vat_accounts = (
            self._chart_of_accounts_repository
            .load_vat_accounts(company_id)
        )
        account_roles = (
            self._chart_of_accounts_repository
            .load_account_roles(company_id)
        )

        if (
            control_accounts is None
            or vat_accounts is None
            or account_roles is None
        ):
            raise RuntimeError(
                "Die Kontenkonfiguration des Mandanten "
                "ist nicht vollständig."
            )

        return (
            control_accounts,
            vat_accounts,
            account_roles,
        )

    def update_account_configuration(
        self,
        *,
        control_accounts: AccountingControlAccounts,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
    ) -> None:
        """Aktualisiert die Kontenkonfiguration des geöffneten Mandanten."""

        if self._chart_of_accounts_repository is None:
            raise RuntimeError(
                "Die Kontenrahmenverwaltung ist nicht konfiguriert."
            )

        (
            self._chart_of_accounts_repository
            .save_account_configuration(
                company_id=(
                    self._context.company.company_id
                ),
                control_accounts=control_accounts,
                vat_accounts=vat_accounts,
                account_roles=account_roles,
            )
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
    def previous_fiscal_year(self) -> FiscalYear | None:
        """Liefert das chronologisch vorherige Geschäftsjahr."""

        fiscal_years = self._company_repository.get_managed_fiscal_years(
            self._context.company.company_id
        )

        previous_fiscal_year: FiscalYear | None = None

        for managed_fiscal_year in fiscal_years:
            if (
                managed_fiscal_year.fiscal_year
                == self._context.fiscal_year
            ):
                return previous_fiscal_year

            previous_fiscal_year = (
                managed_fiscal_year.fiscal_year
            )

        raise ValueError(
            "Das geöffnete Geschäftsjahr wurde nicht gefunden."
        )

    @property
    def is_open(self) -> bool:
        """Gibt an, ob noch Buchungen zulässig sind."""

        return self.managed_fiscal_year.status is FiscalYearStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """Gibt an, ob das Geschäftsjahr abgeschlossen ist."""

        return self.managed_fiscal_year.status is FiscalYearStatus.CLOSED

    def create_reversal_booking(
        self,
        *,
        booking_id: UUID,
        reversal_date: date,
    ) -> Booking:
        """Erzeugt eine Stornobuchung, ohne sie bereits zu persistieren."""

        if not isinstance(booking_id, UUID):
            raise TypeError(
                "booking_id must be a UUID"
            )

        if not isinstance(reversal_date, date):
            raise TypeError(
                "reversal_date muss ein Datum sein."
            )

        if self.is_closed:
            raise ValueError(
                "Ein abgeschlossenes Geschäftsjahr "
                "kann nicht mehr bebucht werden."
            )

        if not self._context.fiscal_year.contains(
            reversal_date
        ):
            raise ValueError(
                "Das Stornodatum liegt außerhalb "
                "des Geschäftsjahres."
            )

        bookings = (
            self._booking_repository
            .list_for_fiscal_year(
                company_id=(
                    self._context.company.company_id
                ),
                fiscal_year=(
                    self._context.fiscal_year
                ),
            )
        )

        original_booking = next(
            (
                booking
                for booking in bookings
                if booking.booking_id == booking_id
            ),
            None,
        )

        if original_booking is None:
            raise ValueError(
                "Die zu stornierende Buchung "
                "wurde nicht gefunden."
            )

        if (
            original_booking.booking_type
            is not BookingType.REGULAR
        ):
            raise ValueError(
                "Nur reguläre Buchungen können "
                "über das Journal storniert werden."
            )

        already_reversed = any(
            booking.booking_type
            is BookingType.REVERSAL
            and booking.reversal_of_booking_id
            == original_booking.booking_id
            for booking in bookings
        )

        if already_reversed:
            raise ValueError(
                "Die Buchung wurde bereits storniert."
            )

        reversed_lines = tuple(
            BookingLine(
                account_number=line.account_number,
                side=(
                    EntrySide.CREDIT
                    if line.side is EntrySide.DEBIT
                    else EntrySide.DEBIT
                ),
                amount=line.amount,
            )
            for line in original_booking.lines
        )

        if original_booking.voucher_no:
            booking_reference = (
                f"Buchung {original_booking.voucher_no}"
            )

            if original_booking.description:
                booking_reference += (
                    f": {original_booking.description}"
                )

        elif original_booking.description:
            booking_reference = (
                original_booking.description
            )

        else:
            booking_reference = (
                f"Buchung {original_booking.booking_id}"
            )

        return Booking(
            booking_date=reversal_date,
            description=(
                f"Storno zu {booking_reference}"
            ),
            booking_type=BookingType.REVERSAL,
            reversal_of_booking_id=(
                original_booking.booking_id
            ),
            lines=reversed_lines,
        )

    def effective_equity_contributions(self) -> Decimal:
        """Ermittelt die wirksamen BVV-Einlagen des Geschäftsjahres."""

        if self._equity_contribution_repository is None:
            return Decimal("0.00")

        references = (
            self._equity_contribution_repository
            .list_for_fiscal_year(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
            )
        )

        total = Decimal("0.00")

        for reference in references:
            if self._booking_repository.is_reversed(
                reference.booking_id
            ):
                continue

            booking = self._booking_repository.get(
                reference.booking_id
            )

            if booking is None:
                raise ValueError(
                    "Die zu einer BVV-Einlage gehörende "
                    "Buchung ist nicht vorhanden."
                )

            position = reference.booking_line_position

            if position >= len(booking.lines):
                raise ValueError(
                    "Die zu einer BVV-Einlage gehörende "
                    "Buchungszeile ist nicht vorhanden."
                )

            total += booking.lines[position].amount

        return total

    def effective_withdrawal_distributions(self) -> Decimal:
        """Ermittelt die wirksamen Ausschüttungen für die BVV."""

        if (
            self._profit_appropriation_posting_repository
            is None
        ):
            return Decimal("0.00")

        postings = (
            self._profit_appropriation_posting_repository
            .list_for_posting_fiscal_year(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
            )
        )

        total = Decimal("0.00")

        for posting in postings:
            if (
                posting.posting_type
                is not ProfitAppropriationPostingType.DISTRIBUTION
            ):
                continue

            if self._booking_repository.is_reversed(
                posting.booking_id
            ):
                continue

            total += posting.amount

        return total

    def post_opening_balance(
        self,
        bookings: tuple[Booking, ...],
    ) -> None:
        """Verbucht eine manuelle Eröffnungsbilanz atomar."""

        if not bookings:
            raise ValueError(
                "Die Eröffnungsbilanz enthält keine Buchungen."
            )

        try:
            self._company_repository.lock_open_fiscal_year(
                self._context.company.company_id,
                self._context.fiscal_year,
            )

            managed_fiscal_year = self.managed_fiscal_year

            if managed_fiscal_year.is_closed:
                raise ValueError(
                    "Das Geschäftsjahr ist bereits abgeschlossen."
                )

            if managed_fiscal_year.has_opening_source:
                raise ValueError(
                    "Das Geschäftsjahr wurde bereits "
                    "aus einem Vorjahr eröffnet."
                )

            existing_bookings = (
                self._booking_repository.list_for_fiscal_year(
                    company_id=self._context.company.company_id,
                    fiscal_year=self._context.fiscal_year,
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

            for booking in bookings:
                if booking.booking_type is not BookingType.OPENING:
                    raise ValueError(
                        "Es sind ausschließlich "
                        "Eröffnungsbuchungen zulässig."
                    )

                if (
                    booking.booking_date
                    != self._context.fiscal_year.start_date
                ):
                    raise ValueError(
                        "Das Buchungsdatum muss dem Beginn "
                        "des Geschäftsjahres entsprechen."
                    )

            for booking in bookings:
                self._booking_repository.add(
                    company_id=self._context.company.company_id,
                    fiscal_year=self._context.fiscal_year,
                    booking=booking,
                    commit=False,
                )

            self._booking_repository.commit()

        except Exception:
            self._booking_repository.rollback()
            raise

        self.reload()

    def post_booking(
        self,
        booking: Booking,
        *,
        equity_contribution_line_positions: tuple[int, ...] = (),
        chart_of_accounts: ChartOfAccountsTemplate | None = None,
    ) -> None:
        """Verbucht und persistiert eine laufende Buchung."""

        if equity_contribution_line_positions:
            self._post_booking_with_equity_contributions(
                booking=booking,
                booking_line_positions=(
                    equity_contribution_line_positions
                ),
                chart_of_accounts=chart_of_accounts,
            )
            return

        if (
            booking.booking_type is not BookingType.REVERSAL
            or self._fixed_asset_movement_repository is None
        ):
            self._booking_repository.add(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                booking=booking,
            )
            self.reload()
            return

        if booking.reversal_of_booking_id is None:
            raise ValueError(
                "Die Stornobuchung verweist auf keine "
                "ursprüngliche Buchung."
            )

        original_movements_with_positions = (
            self._fixed_asset_movement_repository
            .list_with_positions_for_booking(
                booking.reversal_of_booking_id
            )
        )

        if not original_movements_with_positions:
            self._booking_repository.add(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                booking=booking,
            )
            self.reload()
            return

        if self._fixed_asset_repository is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        try:
            self._booking_repository.add(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                booking=booking,
                commit=False,
            )

            for (
                original_movement,
                booking_line_position,
            ) in original_movements_with_positions:
                reversal_movement = FixedAssetMovement(
                    fixed_asset_id=(
                        original_movement.fixed_asset_id
                    ),
                    fiscal_year_end=(
                        self._context.fiscal_year.end_date
                    ),
                    movement_date=booking.booking_date,
                    amount=original_movement.amount,
                    booking_id=booking.booking_id,
                    movement_type=(
                        FixedAssetMovementType.REVERSAL
                    ),
                    reversed_movement_id=(
                        original_movement.movement_id
                    ),
                )

                self._fixed_asset_movement_repository.add(
                    movement=reversal_movement,
                    booking_line_position=(
                        booking_line_position
                    ),
                    commit=False,
                )

                if (
                    original_movement.movement_type
                    is FixedAssetMovementType.DISPOSAL
                ):
                    fixed_asset = (
                        self._fixed_asset_repository.get(
                            original_movement.fixed_asset_id
                        )
                    )

                    if fixed_asset is None:
                        raise ValueError(
                            "Das Anlagegut der zu stornierenden "
                            "Abgangsbuchung ist nicht vorhanden."
                        )

                    restored_fixed_asset = replace(
                        fixed_asset,
                        status=FixedAssetStatus.ACTIVE,
                        disposal_date=None,
                    )

                    self._fixed_asset_repository.update(
                        fixed_asset=restored_fixed_asset,
                        commit=False,
                    )

            self._booking_repository.commit()

        except Exception:
            self._booking_repository.rollback()
            raise

        self.reload()

    def _post_booking_with_equity_contributions(
        self,
        *,
        booking: Booking,
        booking_line_positions: tuple[int, ...],
        chart_of_accounts: ChartOfAccountsTemplate | None,
    ) -> None:
        """Persistiert eine Buchung mit gekennzeichneten Einlagenzeilen."""

        if self._equity_contribution_repository is None:
            raise RuntimeError(
                "Die Einlagenverwaltung ist nicht konfiguriert."
            )

        if chart_of_accounts is None:
            raise ValueError(
                "Für eine Einlagenbuchung ist der Kontenrahmen "
                "erforderlich."
            )

        if booking.booking_type is not BookingType.REGULAR:
            raise ValueError(
                "Nur laufende Buchungen können "
                "Gesellschaftereinlagen enthalten."
            )

        if len(set(booking_line_positions)) != len(
            booking_line_positions
        ):
            raise ValueError(
                "Eine Buchungszeile darf nur einmal als "
                "Gesellschaftereinlage gekennzeichnet werden."
            )

        mapping_rules = {
            rule.account_number: rule
            for rule in chart_of_accounts.account_mapping_rules
        }

        references: list[EquityContributionReference] = []

        for position in booking_line_positions:
            if not isinstance(position, int):
                raise TypeError(
                    "booking_line_positions müssen Ganzzahlen sein."
                )

            if position < 0 or position >= len(booking.lines):
                raise ValueError(
                    "Die Position einer Einlagenzeile ist ungültig."
                )

            line = booking.lines[position]

            if line.side is not EntrySide.CREDIT:
                raise ValueError(
                    "Eine Gesellschaftereinlage muss auf der "
                    "Eigenkapitalseite im Haben gebucht werden."
                )

            mapping_rule = mapping_rules.get(
                line.account_number
            )

            if mapping_rule is None:
                raise ValueError(
                    "Für das Einlagenkonto "
                    f"{line.account_number} ist keine "
                    "HGB-Zuordnung vorhanden."
                )

            credit_position = mapping_rule.credit_position

            if (
                credit_position is None
                or credit_position.code
                not in {
                    "HGB.266.PASSIVA.A.I",
                    "HGB.266.PASSIVA.A.II",
                }
            ):
                raise ValueError(
                    "Als Gesellschaftereinlage können nur "
                    "Buchungszeilen auf gezeichnetes Kapital "
                    "oder Kapitalrücklage gekennzeichnet werden."
                )

            references.append(
                EquityContributionReference(
                    booking_id=booking.booking_id,
                    booking_line_position=position,
                )
            )

        try:
            self._booking_repository.add(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                booking=booking,
                commit=False,
            )

            for reference in references:
                self._equity_contribution_repository.add(
                    company_id=self._context.company.company_id,
                    reference=reference,
                    commit=False,
                )

            self._booking_repository.commit()

        except Exception:
            self._booking_repository.rollback()
            raise

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
        include_opening_balance: bool = True,
    ) -> AccountActivityReport:
        """Erzeugt eine Kontenauswertung für das geöffnete Geschäftsjahr."""

        return self._reporting_service.account_activity_report(
            journal=self._journal,
            account_number=account_number,
            start_date=start_date,
            end_date=end_date,
            include_opening_balance=include_opening_balance,
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

    def list_shareholders(
        self,
    ) -> tuple[Shareholder, ...]:
        """Lädt die Gesellschafter des geöffneten Unternehmens."""

        if self._shareholder_repository is None:
            raise RuntimeError(
                "Die Gesellschafterverwaltung ist nicht konfiguriert."
            )

        return self._shareholder_repository.list_for_company(
            self._context.company.company_id
        )

    def add_shareholder(
        self,
        shareholder: Shareholder,
    ) -> None:
        """Speichert einen Gesellschafter des geöffneten Unternehmens."""

        if self._shareholder_repository is None:
            raise RuntimeError(
                "Die Gesellschafterverwaltung ist nicht konfiguriert."
            )

        if (
            shareholder.company_id
            != self._context.company.company_id
        ):
            raise ValueError(
                "Der Gesellschafter gehört nicht zum "
                "geöffneten Unternehmen."
            )

        self._shareholder_repository.add(
            shareholder=shareholder
        )

    def update_shareholder(
        self,
        shareholder: Shareholder,
    ) -> None:
        """Aktualisiert einen Gesellschafter des geöffneten Unternehmens."""

        if self._shareholder_repository is None:
            raise RuntimeError(
                "Die Gesellschafterverwaltung ist nicht konfiguriert."
            )

        if (
            shareholder.company_id
            != self._context.company.company_id
        ):
            raise ValueError(
                "Der Gesellschafter gehört nicht zum "
                "geöffneten Unternehmen."
            )

        self._shareholder_repository.update(
            shareholder=shareholder
        )

    def delete_shareholder(
        self,
        shareholder_id: UUID,
    ) -> None:
        """Löscht einen Gesellschafter des geöffneten Unternehmens."""


        if self._shareholder_repository is None:
            raise RuntimeError(
                "Die Gesellschafterverwaltung ist nicht konfiguriert."
            )

        shareholder = self._shareholder_repository.get(
            shareholder_id
        )

        if shareholder is None:
            raise ValueError(
                "Der Gesellschafter ist nicht vorhanden."
            )

        if (
            shareholder.company_id
            != self._context.company.company_id
        ):
            raise ValueError(
                "Der Gesellschafter gehört nicht zum "
                "geöffneten Unternehmen."
            )

        self._shareholder_repository.delete(
            shareholder_id=shareholder_id
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

    def fixed_asset_accumulated_depreciation(
        self,
        fixed_asset_id: UUID,
    ) -> Decimal:
        """Liefert die wirksame kumulierte AfA eines Anlageguts."""

        if self._fixed_asset_depreciation_repository is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        depreciations = (
            self._fixed_asset_depreciation_repository
            .list_for_fixed_asset(
                fixed_asset_id
            )
        )

        effective_depreciations = (
            self._effective_fixed_asset_depreciations(
                depreciations
            )
        )

        return sum(
            (
                depreciation.amount
                for depreciation in effective_depreciations
            ),
            start=Decimal("0.00"),
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

    @staticmethod
    def _effective_fixed_asset_movements(
        movements: tuple[FixedAssetMovement, ...],
    ) -> tuple[FixedAssetMovement, ...]:
        """Liefert die nicht stornierten Anlagenbewegungen."""

        reversed_movement_ids = {
            movement.reversed_movement_id
            for movement in movements
            if (
                movement.movement_type
                is FixedAssetMovementType.REVERSAL
                and movement.reversed_movement_id is not None
            )
        }

        return tuple(
            movement
            for movement in movements
            if (
                movement.movement_type
                is not FixedAssetMovementType.REVERSAL
                and movement.movement_id
                not in reversed_movement_ids
            )
        )

    def build_fixed_asset_disposal_details(
        self,
        *,
        control_accounts: AccountingControlAccounts,
    ) -> tuple[FixedAssetDisposalDetail, ...]:
        """Ermittelt die wirksamen Anlagenabgänge des Geschäftsjahres."""

        if self._fixed_asset_repository is None:
            return ()

        if self._fixed_asset_movement_repository is None:
            return ()

        details: list[FixedAssetDisposalDetail] = []

        for fixed_asset in self.list_fixed_assets():
            movements = (
                self._fixed_asset_movement_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            effective_movements = (
                self._effective_fixed_asset_movements(
                    movements
                )
            )

            for movement in effective_movements:
                if (
                    movement.movement_type
                    is not FixedAssetMovementType.DISPOSAL
                ):
                    continue

                if (
                    movement.fiscal_year_end
                    != self._context.fiscal_year.end_date
                ):
                    continue

                booking = self._booking_repository.get(
                    movement.booking_id
                )

                if booking is None:
                    raise ValueError(
                        "Die Buchung des Anlagenabgangs "
                        "ist nicht vorhanden."
                    )

                movement_positions = (
                    self._fixed_asset_movement_repository
                    .list_with_positions_for_booking(
                        movement.booking_id
                    )
                )

                asset_line_position = next(
                    (
                        position
                        for (
                            linked_movement,
                            position,
                        ) in movement_positions
                        if (
                            linked_movement.movement_id
                            == movement.movement_id
                        )
                    ),
                    None,
                )

                if asset_line_position is None:
                    raise ValueError(
                        "Die Buchungszeile des Anlagenabgangs "
                        "ist nicht vorhanden."
                    )

                try:
                    asset_line = booking.lines[
                        asset_line_position
                    ]
                except IndexError as exc:
                    raise ValueError(
                        "Die Buchungszeile des Anlagenabgangs "
                        "ist nicht vorhanden."
                    ) from exc

                carrying_amount = asset_line.amount

                gain = sum(
                    (
                        line.amount
                        for line in booking.lines
                        if (
                            line.account_number
                            == control_accounts
                            .fixed_asset_disposal_gain_account
                            and line.side is EntrySide.CREDIT
                        )
                    ),
                    start=Decimal("0.00"),
                )

                loss = sum(
                    (
                        line.amount
                        for line in booking.lines
                        if (
                            line.account_number
                            == control_accounts
                            .fixed_asset_disposal_loss_account
                            and line.side is EntrySide.DEBIT
                        )
                    ),
                    start=Decimal("0.00"),
                )

                net_proceeds = (
                    carrying_amount
                    + gain
                    - loss
                )

                details.append(
                    FixedAssetDisposalDetail(
                        position_code=fixed_asset.position_code,
                        carrying_amount=carrying_amount,
                        net_proceeds=net_proceeds,
                    )
                )

        return tuple(details)

    def has_fixed_asset_acquisition(
        self,
        fixed_asset_id: UUID,
    ) -> bool:
        """Prüft, ob eine wirksame Anschaffungsbuchung zugeordnet ist."""

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

        effective_movements = (
            self._effective_fixed_asset_movements(
                movements
            )
        )

        return any(
            movement.movement_type
            is FixedAssetMovementType.ACQUISITION
            for movement in effective_movements
        )


    def update_fixed_asset(
        self,
        fixed_asset: FixedAsset,
    ) -> None:
        """Aktualisiert ein noch änderbares Anlagegut atomar."""

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

        try:
            self._company_repository.lock_open_fiscal_year(
                self._context.company.company_id,
                self._context.fiscal_year,
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

            effective_movements = (
                self._effective_fixed_asset_movements(
                    movements
                )
            )

            acquisition_linked = any(
                movement.movement_type
                is FixedAssetMovementType.ACQUISITION
                for movement in effective_movements
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
                fixed_asset=fixed_asset,
                commit=False,
            )

            self._booking_repository.commit()

        except Exception:
            self._booking_repository.rollback()
            raise


    def delete_fixed_asset(
        self,
        fixed_asset_id: UUID,
    ) -> None:
        """Löscht ein noch nicht buchungswirksames Anlagegut atomar."""

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

        try:
            self._company_repository.lock_open_fiscal_year(
                self._context.company.company_id,
                self._context.fiscal_year,
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
                fixed_asset_id=fixed_asset_id,
                commit=False,
            )

            self._booking_repository.commit()

        except Exception:
            self._booking_repository.rollback()
            raise


    def link_fixed_asset_acquisition(
        self,
        *,
        fixed_asset_id: UUID,
        booking_id: UUID,
        booking_line_position: int,
    ) -> FixedAssetMovement:
        """Ordnet eine Anschaffungsbuchung einem Anlagegut atomar zu."""

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

        if not isinstance(fixed_asset_id, UUID):
            raise TypeError("fixed_asset_id must be a UUID")

        if not isinstance(booking_id, UUID):
            raise TypeError("booking_id must be a UUID")

        if not isinstance(booking_line_position, int):
            raise TypeError(
                "booking_line_position must be an int"
            )

        if booking_line_position < 0:
            raise ValueError(
                "booking_line_position must not be negative"
            )

        try:
            # Vor sämtlichen fachlichen Datenbankabfragen sperren.
            self._company_repository.lock_open_fiscal_year(
                self._context.company.company_id,
                self._context.fiscal_year,
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

            if booking_line_position >= len(booking.lines):
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

            effective_movements = (
                self._effective_fixed_asset_movements(
                    existing_movements
                )
            )

            if any(
                movement.movement_type
                is FixedAssetMovementType.ACQUISITION
                for movement in effective_movements
            ):
                raise ValueError(
                    "Dem Anlagegut ist bereits eine "
                    "Anschaffungsbuchung zugeordnet."
                )

            movement = FixedAssetMovement(
                fixed_asset_id=fixed_asset.fixed_asset_id,
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
                commit=False,
            )

            self._booking_repository.commit()

            return movement

        except Exception:
            self._booking_repository.rollback()
            raise


    def link_fixed_asset_disposal(
        self,
        *,
        fixed_asset_id: UUID,
        booking_id: UUID,
        booking_line_position: int,
    ) -> FixedAssetMovement:
        """Ordnet einem Anlagegut eine vorhandene Abgangsbuchung zu."""

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

        if not isinstance(fixed_asset_id, UUID):
            raise TypeError("fixed_asset_id must be a UUID")

        if not isinstance(booking_id, UUID):
            raise TypeError("booking_id must be a UUID")

        if not isinstance(booking_line_position, int):
            raise TypeError(
                "booking_line_position must be an int"
            )

        if booking_line_position < 0:
            raise ValueError(
                "booking_line_position must not be negative"
            )


        try:
            # Die Sperre muss vor sämtlichen Datenbankprüfungen
            # erworben werden, damit konkurrierende Benutzer
            # nicht denselben veralteten Anlagenstatus verwenden.
            self._company_repository.lock_open_fiscal_year(
                self._context.company.company_id,
                self._context.fiscal_year,
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
                    "Das Anlagegut ist bereits abgegangen."
                )

            booking = self._booking_repository.get(
                booking_id
            )

            if booking is None:
                raise ValueError(
                    "Die Buchung ist nicht vorhanden."
                )

            if not (
                self._context.fiscal_year.start_date
                <= booking.booking_date
                <= self._context.fiscal_year.end_date
            ):
                raise ValueError(
                    "Die Buchung gehört nicht zum "
                    "geöffneten Geschäftsjahr."
                )

            if booking.booking_date < fixed_asset.acquisition_date:
                raise ValueError(
                    "Der Anlagenabgang kann nicht vor dem "
                    "Anschaffungsdatum liegen."
                )

            if booking_line_position >= len(booking.lines):
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

            if booking_line.side is not EntrySide.CREDIT:
                raise ValueError(
                    "Die Abgangsbuchung muss das Anlagenkonto "
                    "im Haben buchen."
                )

            existing_movements = (
                self._fixed_asset_movement_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            effective_movements = (
                self._effective_fixed_asset_movements(
                    existing_movements
                )
            )

            if not any(
                movement.movement_type
                is FixedAssetMovementType.ACQUISITION
                for movement in effective_movements
            ):
                raise ValueError(
                    "Dem Anlagegut ist noch keine "
                    "Anschaffungsbuchung zugeordnet."
                )

            if any(
                movement.movement_type
                is FixedAssetMovementType.DISPOSAL
                for movement in effective_movements
            ):
                raise ValueError(
                    "Dem Anlagegut ist bereits eine "
                    "Abgangsbuchung zugeordnet."
                )

            if self._fixed_asset_depreciation_repository is None:
                raise RuntimeError(
                    "Die Anlagenbuchhaltung ist nicht konfiguriert."
                )

            depreciations = (
                self._fixed_asset_depreciation_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            effective_depreciations = (
                self._effective_fixed_asset_depreciations(
                    depreciations
                )
            )

            current_year_depreciations = tuple(
                depreciation
                for depreciation in effective_depreciations
                if depreciation.fiscal_year_end
                == self._context.fiscal_year.end_date
            )

            if current_year_depreciations:
                raise ValueError(
                    "Für das Anlagegut ist bereits eine "
                    "Abschreibung für dieses Geschäftsjahr "
                    "gebucht. Die Abschreibung muss vor "
                    "Zuordnung des Anlagenabgangs storniert "
                    "werden."
                )

            movement = FixedAssetMovement(
                fixed_asset_id=fixed_asset.fixed_asset_id,
                fiscal_year_end=(
                    self._context.fiscal_year.end_date
                ),
                movement_date=booking.booking_date,
                amount=booking_line.amount,
                booking_id=booking.booking_id,
                movement_type=FixedAssetMovementType.DISPOSAL,
            )

            self._fixed_asset_movement_repository.add(
                movement=movement,
                booking_line_position=booking_line_position,
                commit=False,
            )

            disposed_fixed_asset = replace(
                fixed_asset,
                status=FixedAssetStatus.DISPOSED,
                disposal_date=booking.booking_date,
            )

            self._fixed_asset_repository.update(
                fixed_asset=disposed_fixed_asset,
                commit=False,
            )

            # Anlagenbewegung und Anlagenstatus werden
            # gemeinsam und atomar gespeichert.
            self._booking_repository.commit()

            return movement

        except Exception:
            self._booking_repository.rollback()
            raise


    def build_fixed_asset_disposal_preview(
        self,
        *,
        fixed_asset_id: UUID,
        disposal_date: date,
        gross_proceeds: Decimal,
        tax_rate: int,
        counter_account_number: str,
        voucher_no: str | None = None,
        description: str | None = None,
    ) -> FixedAssetDisposalPreview:
        """Erstellt die Vorschau eines Anlagenverkaufs."""

        if not self.is_open:
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if (
            self._fixed_asset_repository is None
            or self._fixed_asset_depreciation_repository is None
            or self._fixed_asset_movement_repository is None
            or self._depreciation_service is None
        ):
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
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
                "Das Anlagegut ist nicht aktiv."
            )

        if not self._context.fiscal_year.contains(
            disposal_date
        ):
            raise ValueError(
                "Das Abgangsdatum liegt außerhalb "
                "des Geschäftsjahres."
            )

        if disposal_date < fixed_asset.acquisition_date:
            raise ValueError(
                "Das Abgangsdatum liegt vor dem "
                "Anschaffungsdatum."
            )

        movements = (
            self._fixed_asset_movement_repository
            .list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        effective_movements = (
            self._effective_fixed_asset_movements(
                movements
            )
        )

        has_acquisition = any(
            movement.movement_type
            is FixedAssetMovementType.ACQUISITION
            for movement in effective_movements
        )

        if not has_acquisition:
            raise ValueError(
                "Dem Anlagegut ist keine wirksame "
                "Anschaffungsbuchung zugeordnet."
            )

        has_disposal = any(
            movement.movement_type
            is FixedAssetMovementType.DISPOSAL
            for movement in effective_movements
        )

        if has_disposal:
            raise ValueError(
                "Dem Anlagegut ist bereits ein "
                "wirksamer Anlagenabgang zugeordnet."
            )

        depreciations = (
            self._fixed_asset_depreciation_repository
            .list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        effective_depreciations = (
            self._effective_fixed_asset_depreciations(
                depreciations
            )
        )

        current_year_depreciations = tuple(
            depreciation
            for depreciation in effective_depreciations
            if (
                self._context.fiscal_year.contains(
                    depreciation.depreciation_date
                )
            )
        )

        previous_depreciation = sum(
            (
                depreciation.amount
                for depreciation in effective_depreciations
                if depreciation
                not in current_year_depreciations
            ),
            Decimal("0.00"),
        )

        depreciation_proposal = None

        if current_year_depreciations:
            if len(current_year_depreciations) != 1:
                raise ValueError(
                    "Für das Anlagegut sind mehrere "
                    "wirksame Abschreibungen im aktuellen "
                    "Geschäftsjahr vorhanden."
                )

            current_depreciation = (
                current_year_depreciations[0]
            )

            if (
                current_depreciation.depreciation_date
                != disposal_date
            ):
                raise ValueError(
                    "Für das Anlagegut ist bereits eine "
                    "Abschreibung mit einem anderen "
                    "Abschreibungsdatum gebucht."
                )

            accumulated_depreciation = sum(
                (
                    depreciation.amount
                    for depreciation
                    in effective_depreciations
                ),
                Decimal("0.00"),
            )

        else:
            depreciation_proposal = (
                self._depreciation_service.build_proposal(
                    fixed_asset=fixed_asset,
                    fiscal_year=self._context.fiscal_year,
                    previous_depreciation=(
                        previous_depreciation
                    ),
                    expense_account_number=(
                        fixed_asset
                        .depreciation_expense_account_number
                    ),
                    asset_account_number=(
                        fixed_asset.asset_account_number
                    ),
                    depreciation_end_date=disposal_date,
                )
            )

            accumulated_depreciation = (
                previous_depreciation
                + (
                    depreciation_proposal.amount
                    if depreciation_proposal is not None
                    else Decimal("0.00")
                )
            )

        (
            control_accounts,
            vat_accounts,
            _account_roles,
        ) = self.load_account_configuration()

        disposal_calculation = (
            self._fixed_asset_disposal_service.calculate(
                booking_date=disposal_date,
                acquisition_cost=(
                    fixed_asset.acquisition_cost
                ),
                accumulated_depreciation=(
                    accumulated_depreciation
                ),
                gross_proceeds=gross_proceeds,
                tax_rate=tax_rate,
                asset_account_number=(
                    fixed_asset.asset_account_number
                ),
                counter_account_number=(
                    counter_account_number
                ),
                control_accounts=control_accounts,
                vat_accounts=vat_accounts,
                voucher_no=voucher_no,
                description=description,
            )
        )

        return FixedAssetDisposalPreview(
            fixed_asset=fixed_asset,
            previous_depreciation=previous_depreciation,
            depreciation_proposal=depreciation_proposal,
            accumulated_depreciation=accumulated_depreciation,
            disposal_calculation=disposal_calculation,
            tax_rate=tax_rate,
            counter_account_number=counter_account_number,
        )

    def confirm_fixed_asset_disposal(
        self,
        preview: FixedAssetDisposalPreview,
    ) -> FixedAssetMovement:
        """Bestätigt einen Anlagenverkauf mit Aktualitätsprüfung."""

        if not self.is_open:
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if self._fixed_asset_disposal_workflow is None:
            raise RuntimeError(
                "Der Anlagenabgang ist nicht konfiguriert."
            )

        original = preview.disposal_calculation
        original_booking = original.booking

        try:
            # Sperre muss bis zum Commit der Verkaufsbuchung bestehen.
            self._company_repository.lock_open_fiscal_year(
                self._context.company.company_id,
                self._context.fiscal_year,
            )

            current = self.build_fixed_asset_disposal_preview(
                fixed_asset_id=preview.fixed_asset.fixed_asset_id,
                disposal_date=original_booking.booking_date,
                gross_proceeds=original.gross_proceeds,
                tax_rate=preview.tax_rate,
                counter_account_number=preview.counter_account_number,
                voucher_no=original_booking.voucher_no,
                description=original_booking.description,
            )

            current_calculation = current.disposal_calculation
            current_booking = current_calculation.booking

            # Ein inzwischen geänderter Anlagenstammsatz
            # macht die ursprüngliche Bestätigung ungültig.
            asset_changed = (
                current.fixed_asset != preview.fixed_asset
            )

            # Die Abschreibungssituation muss unverändert sein.
            depreciation_changed = (
                current.previous_depreciation
                != preview.previous_depreciation
                or current.accumulated_depreciation
                != preview.accumulated_depreciation
                or current.depreciation_proposal
                != preview.depreciation_proposal
            )

            # Fachliche Buchungswerte vergleichen, nicht die
            # neu erzeugte Buchungs-ID.
            calculation_changed = any(
                (
                    current_calculation.acquisition_cost
                    != original.acquisition_cost,
                    current_calculation.accumulated_depreciation
                    != original.accumulated_depreciation,
                    current_calculation.carrying_amount
                    != original.carrying_amount,
                    current_calculation.gross_proceeds
                    != original.gross_proceeds,
                    current_calculation.net_proceeds
                    != original.net_proceeds,
                    current_calculation.tax_amount
                    != original.tax_amount,
                    current_calculation.gain
                    != original.gain,
                    current_calculation.loss
                    != original.loss,
                    current_booking.lines
                    != original_booking.lines,
                )
            )

            if (
                asset_changed
                or depreciation_changed
                or calculation_changed
                or current.depreciation_proposal is not None
            ):
                raise ValueError(
                    "Die Daten des Anlagenverkaufs haben sich "
                    "seit der Vorschau geändert oder es ist "
                    "noch eine Abschreibung erforderlich.\n\n"
                    "Der Verkauf wurde nicht gebucht. "
                    "Bitte erstellen und bestätigen Sie "
                    "die Verkaufsvorschau erneut."
                )

            movement = self._fixed_asset_disposal_workflow.confirm(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                fixed_asset=current.fixed_asset,
                calculation=original,
            )

        except Exception:
            self._booking_repository.rollback()
            raise

        self.reload()

        return movement

    def _effective_fixed_asset_depreciations(
        self,
        depreciations: tuple[FixedAssetDepreciation, ...],
    ) -> tuple[FixedAssetDepreciation, ...]:
        """Liefert die nicht stornierten Anlagenabschreibungen."""

        bookings = self._booking_repository.list_for_fiscal_year(
            company_id=self._context.company.company_id,
            fiscal_year=self._context.fiscal_year,
        )

        reversed_booking_ids = {
            booking.reversal_of_booking_id
            for booking in bookings
            if (
                booking.booking_type is BookingType.REVERSAL
                and booking.reversal_of_booking_id is not None
            )
        }

        return tuple(
            depreciation
            for depreciation in depreciations
            if depreciation.booking_id not in reversed_booking_ids
        )

    def list_confirmed_depreciations(
        self,
    ) -> tuple[FixedAssetDepreciation, ...]:
        """Lädt bestätigte Abschreibungen des geöffneten Geschäftsjahres."""

        if (
            self._fixed_asset_repository is None
            or self._fixed_asset_depreciation_repository is None
        ):
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        assets = self._fixed_asset_repository.list_for_company(
            self._context.company.company_id
        )

        depreciations: list[FixedAssetDepreciation] = []

        for asset in assets:
            asset_depreciations = (
                self._fixed_asset_depreciation_repository
                .list_for_fixed_asset(
                    asset.fixed_asset_id
                )
            )

            depreciations.extend(
                depreciation
                for depreciation in asset_depreciations
                if depreciation.fiscal_year_end
                == self._context.fiscal_year.end_date
            )

        return self._effective_fixed_asset_depreciations(
            tuple(depreciations)
        )

    def get_tax_depreciation_adjustment(
        self,
        depreciation_id: UUID,
    ) -> TaxDepreciationAdjustment | None:
        """Lädt die steuerliche AfA-Abweichung einer Abschreibung."""

        if self._tax_depreciation_adjustment_repository is None:
            raise RuntimeError(
                "Steuerliche AfA-Abweichungen sind nicht konfiguriert."
            )

        return (
            self._tax_depreciation_adjustment_repository
            .get_for_depreciation(
                depreciation_id
            )
        )

    def tax_depreciation_differences_for_bga(
        self,
    ) -> tuple[Decimal, Decimal]:
        """
        Ermittelt steuerliche AfA-Abweichungen für BGA.

        Der erste Rückgabewert enthält die AfA-Differenz des
        geöffneten Geschäftsjahres.

        Der zweite Rückgabewert enthält die kumulierte AfA-Differenz
        aller vorherigen Geschäftsjahre.

        Die AfA-Differenz ist definiert als:

            steuerliche AfA - handelsrechtliche AfA
        """

        if (
            self._fixed_asset_repository is None
            or self._fixed_asset_depreciation_repository is None
        ):
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        if self._tax_depreciation_adjustment_repository is None:
            raise RuntimeError(
                "Steuerliche AfA-Abweichungen sind nicht konfiguriert."
            )

        assets = self._fixed_asset_repository.list_for_company(
            self._context.company.company_id
        )

        current_difference = Decimal("0.00")
        previous_difference = Decimal("0.00")

        current_fiscal_year_end = (
            self._context.fiscal_year.end_date
        )

        for asset in assets:
            if (
                asset.position_code
                != "HGB.266.AKTIVA.A.II.3"
            ):
                continue

            depreciations = (
                self._fixed_asset_depreciation_repository
                .list_for_fixed_asset(
                    asset.fixed_asset_id
                )
            )

            for depreciation in depreciations:
                if (
                    depreciation.fiscal_year_end
                    > current_fiscal_year_end
                ):
                    continue

                adjustment = (
                    self._tax_depreciation_adjustment_repository
                    .get_for_depreciation(
                        depreciation.depreciation_id
                    )
                )

                if adjustment is None:
                    continue

                if (
                    depreciation.fiscal_year_end
                    == current_fiscal_year_end
                ):
                    current_difference += (
                        adjustment.difference
                    )
                else:
                    previous_difference += (
                        adjustment.difference
                    )

        return (
            current_difference,
            previous_difference,
        )

    def tax_depreciation_difference_for_bga(
        self,
    ) -> Decimal:
        """Summiert steuerliche AfA-Abweichungen für BGA im Geschäftsjahr."""

        (
            current_difference,
            _previous_difference,
        ) = self.tax_depreciation_differences_for_bga()

        return current_difference

    def save_tax_depreciation_adjustment(
        self,
        *,
        depreciation_id: UUID,
        tax_amount: Decimal,
    ) -> TaxDepreciationAdjustment | None:
        """Speichert die steuerliche AfA-Abweichung einer Abschreibung."""

        if self._tax_depreciation_adjustment_repository is None:
            raise RuntimeError(
                "Steuerliche AfA-Abweichungen sind nicht konfiguriert."
            )

        return self._tax_depreciation_adjustment_repository.save(
            depreciation_id=depreciation_id,
            tax_amount=tax_amount,
        )

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
            movements = (
                self._fixed_asset_movement_repository
                .list_for_fixed_asset(
                    asset.fixed_asset_id
                )
            )

            effective_movements = (
                self._effective_fixed_asset_movements(
                    movements
                )
            )

            if not any(
                movement.movement_type
                is FixedAssetMovementType.ACQUISITION
                for movement in effective_movements
            ):
                continue

            disposal_movement = next(
                (
                    movement
                    for movement in effective_movements
                    if movement.movement_type
                    is FixedAssetMovementType.DISPOSAL
                ),
                None,
            )

            depreciation_end_date = (
                disposal_movement.movement_date
                if disposal_movement is not None
                else None
            )

            depreciations = (
                self._fixed_asset_depreciation_repository
                .list_for_fixed_asset(
                    asset.fixed_asset_id
                )
            )

            effective_depreciations = (
                self._effective_fixed_asset_depreciations(
                    depreciations
                )
            )

            already_confirmed = any(
                depreciation.fiscal_year_end
                == self._context.fiscal_year.end_date
                for depreciation in effective_depreciations
            )

            if already_confirmed:
                continue

            previous_depreciation = sum(
                (
                    depreciation.amount
                    for depreciation
                    in effective_depreciations
                ),
                start=Decimal("0.00"),
            )

            proposal = self._depreciation_service.build_proposal(
                fixed_asset=asset,
                fiscal_year=self._context.fiscal_year,
                previous_depreciation=(
                    previous_depreciation
                ),
                expense_account_number=(
                    asset.depreciation_expense_account_number
                ),
                asset_account_number=(
                    asset.asset_account_number
                ),
                depreciation_end_date=(
                    depreciation_end_date
                ),
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

        if self._fixed_asset_depreciation_workflow is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        if self._fixed_asset_repository is None:
            raise RuntimeError(
                "Die Anlagenbuchhaltung ist nicht konfiguriert."
            )

        fixed_asset = self._fixed_asset_repository.get(
            proposal.fixed_asset_id
        )

        if fixed_asset is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
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
                asset_description=(
                    fixed_asset.description
                ),
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
        *,
        expected_master_data: CompanyMasterData | None = None,
    ) -> None:
        """Speichert die Stammdaten des geöffneten Unternehmens."""

        if master_data.company != self._context.company:
            raise ValueError(
                "Die Stammdaten gehören nicht zum "
                "geöffneten Unternehmen."
            )

        if expected_master_data is None:
            self._company_repository.save_master_data(
                master_data
            )
        else:
            self._company_repository.save_master_data(
                master_data,
                expected_master_data=expected_master_data,
            )

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

    def _effective_profit_appropriation_postings(
        self,
        postings: tuple[ProfitAppropriationPosting, ...],
    ) -> tuple[ProfitAppropriationPosting, ...]:
        """Liefert die nicht stornierten Ergebnisverwendungsbuchungen."""

        return tuple(
            posting
            for posting in postings
            if not self._booking_repository.is_reversed(
                posting.booking_id
            )
        )

    def has_effective_profit_appropriation_postings(
        self,
    ) -> bool:
        """Prüft auf wirksame Umsetzungsbuchungen des aktuellen Geschäftsjahres."""

        if self._profit_appropriation_posting_repository is None:
            raise RuntimeError(
                "Die Ergebnisverwendungsbuchungen sind nicht konfiguriert."
            )

        postings = (
            self._profit_appropriation_posting_repository
            .list_for_source_fiscal_year(
                company_id=self._context.company.company_id,
                source_fiscal_year_end=(
                    self._context.fiscal_year.end_date
                ),
            )
        )

        return bool(
            self._effective_profit_appropriation_postings(
                postings
            )
        )

    def build_profit_appropriation_posting_proposals(
        self,
        *,
        booking_date: date,
    ) -> tuple[ProfitAppropriationPostingProposal, ...]:
        """Ermittelt offene Buchungsvorschläge zur Ergebnisverwendung des Vorjahres."""

        if not self.is_open:
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if (
            self._profit_appropriation_annual_data_repository is None
            or self._profit_appropriation_posting_repository is None
            or self._chart_of_accounts_repository is None
        ):
            raise RuntimeError(
                "Die Ergebnisverwendungsbuchungen sind nicht konfiguriert."
            )

        if not isinstance(booking_date, date):
            raise TypeError(
                "booking_date muss ein Datum sein."
            )

        if not self._context.fiscal_year.contains(
            booking_date
        ):
            raise ValueError(
                "Das Buchungsdatum liegt außerhalb "
                "des Geschäftsjahres."
            )

        source_fiscal_year = (
            self.managed_fiscal_year.opening_source
        )

        if source_fiscal_year is None:
            return ()

        annual_data = (
            self._profit_appropriation_annual_data_repository
            .get_for_fiscal_year(
                company_id=self._context.company.company_id,
                fiscal_year=source_fiscal_year,
            )
        )

        if annual_data is None:
            return ()

        control_accounts, _, _ = (
            self.load_account_configuration()
        )

        proposals = (
            self._profit_appropriation_posting_service
            .build_proposals(
                data=annual_data,
                booking_date=booking_date,
                control_accounts=control_accounts,
            )
        )

        postings = (
            self._profit_appropriation_posting_repository
            .list_for_source_fiscal_year(
                company_id=self._context.company.company_id,
                source_fiscal_year_end=(
                    source_fiscal_year.end_date
                ),
            )
        )

        effective_postings = (
            self._effective_profit_appropriation_postings(
                postings
            )
        )

        confirmed_types = {
            posting.posting_type
            for posting in effective_postings
        }

        return tuple(
            proposal
            for proposal in proposals
            if proposal.posting_type not in confirmed_types
        )

    def confirm_profit_appropriation_posting(
        self,
        proposal: ProfitAppropriationPostingProposal,
    ) -> ProfitAppropriationPosting:
        """Bucht einen bestätigten Vorschlag zur Ergebnisverwendung."""

        if not self.is_open:
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if self._profit_appropriation_posting_workflow is None:
            raise RuntimeError(
                "Die Ergebnisverwendungsbuchungen sind nicht konfiguriert."
            )

        source_fiscal_year = (
            self.managed_fiscal_year.opening_source
        )

        if source_fiscal_year is None:
            raise ValueError(
                "Das Geschäftsjahr hat kein Eröffnungsquelljahr."
            )

        posting = (
            self._profit_appropriation_posting_workflow.confirm(
                company_id=self._context.company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=self._context.fiscal_year,
                proposal=proposal,
            )
        )

        self.reload()

        return posting

    def load_profit_appropriation_annual_data(
        self,
    ) -> ProfitAppropriationAnnualData | None:
        """Lädt die Ergebnisverwendung des aktuellen Geschäftsjahres."""

        if self._profit_appropriation_annual_data_repository is None:
            raise RuntimeError(
                "Die Ergebnisverwendungsverwaltung ist nicht konfiguriert."
            )

        return (
            self._profit_appropriation_annual_data_repository
            .get_for_fiscal_year(
                company_id=(
                    self._context.company.company_id
                ),
                fiscal_year=(
                    self._context.fiscal_year
                ),
            )
        )

    def save_profit_appropriation_annual_data(
        self,
        data: ProfitAppropriationAnnualData,
        *,
        expected_data: ProfitAppropriationAnnualData | None,
    ) -> None:
        """Speichert den Beschluss mit Sperre und Aktualitätsprüfung."""

        if self._profit_appropriation_annual_data_repository is None:
            raise RuntimeError(
                "Die Ergebnisverwendungsverwaltung ist nicht konfiguriert."
            )

        try:
            self._company_repository.lock_fiscal_year(
                self._context.company.company_id,
                self._context.fiscal_year,
            )

            current_data = (
                self._profit_appropriation_annual_data_repository
                .get_for_fiscal_year(
                    company_id=self._context.company.company_id,
                    fiscal_year=self._context.fiscal_year,
                )
            )

            if current_data != expected_data:
                raise ValueError(
                    "Der Ergebnisverwendungsbeschluss wurde "
                    "zwischenzeitlich von einem anderen Benutzer "
                    "geändert. Ihre Änderungen wurden nicht "
                    "gespeichert. Bitte öffnen Sie den Beschluss "
                    "erneut."
                )

            if self.has_effective_profit_appropriation_postings():
                raise ValueError(
                    "Der Ergebnisverwendungsbeschluss kann nicht geändert "
                    "werden, solange wirksame Umsetzungsbuchungen vorhanden "
                    "sind. Stornieren Sie diese Buchungen zunächst."
                )

            self._profit_appropriation_annual_data_repository.save_for_fiscal_year(
                company_id=self._context.company.company_id,
                fiscal_year=self._context.fiscal_year,
                data=data,
                commit=False,
            )

            self._company_repository.commit()

        except Exception:
            self._company_repository.rollback()
            raise

    def previous_profit_loss_carryforward(
        self,
    ) -> Decimal:
        """Ermittelt den Gewinn-/Verlustvortrag zu Jahresbeginn."""

        control_accounts, _, _ = (
            self.load_account_configuration()
        )

        report = self.build_trial_balance_report(
            start_date=self._context.fiscal_year.start_date,
            end_date=self._context.fiscal_year.end_date,
            opening_balance_account_number=(
                control_accounts.opening_balance_account
            ),
        )

        return (
            self._profit_appropriation_service
            .previous_profit_loss_carryforward(
                trial_balance_report=report,
                profit_loss_carryforward_account=(
                    control_accounts
                    .profit_loss_carryforward_account
                ),
            )
        )

    def validate_profit_appropriation(
        self,
        *,
        net_income: Decimal,
        data: ProfitAppropriationAnnualData,
    ) -> ClosingConsistencyResult:
        """Prüft die Ergebnisverwendung des Geschäftsjahres."""

        previous_profit_loss_carryforward = (
            self.previous_profit_loss_carryforward()
        )

        return self._profit_appropriation_service.validate(
            net_income=net_income,
            previous_profit_loss_carryforward=(
                previous_profit_loss_carryforward
            ),
            data=data,
        )

    def build_bvv_evaluation(
        self,
        *,
        preparation: EBilanzPreparationResult,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> BvvEvaluation:
        """Ermittelt den BVV vollständig aus den Buchführungsdaten."""

        equity_position = next(
            (
                position
                for position in preparation.balance_sheet.liabilities.children
                if position.code == "HGB.266.PASSIVA.A"
            ),
            None,
        )

        if equity_position is None:
            raise ValueError(
                "Die HGB-Eigenkapitalposition "
                "HGB.266.PASSIVA.A fehlt."
            )

        current_hgb_equity = (
            preparation.balance_sheet.amount_for(
                equity_position
            )
        )

        previous_hgb_equity = self.opening_hgb_equity(
            chart_of_accounts=chart_of_accounts,
        )

        current_depreciation_difference = Decimal("0.00")
        previous_depreciation_difference = Decimal("0.00")

        if (
            self._fixed_asset_repository is not None
            and self._fixed_asset_depreciation_repository is not None
            and self._tax_depreciation_adjustment_repository is not None
        ):
            (
                current_depreciation_difference,
                previous_depreciation_difference,
            ) = self.tax_depreciation_differences_for_bga()

        current_book_value_difference = (
            -current_depreciation_difference
        )
        previous_book_value_difference = (
            -previous_depreciation_difference
        )

        contribution = self.effective_equity_contributions()
        withdrawal_distribution = (
            self.effective_withdrawal_distributions()
        )

        values = BvvValueBuilder.build(
            current_hgb_equity=current_hgb_equity,
            previous_hgb_equity=previous_hgb_equity,
            current_book_value_difference=(
                current_book_value_difference
            ),
            previous_book_value_difference=(
                previous_book_value_difference
            ),
            contribution=contribution,
            withdrawal_distribution=(
                withdrawal_distribution
            ),
        )

        return BvvEvaluation(
            current_hgb_equity=current_hgb_equity,
            previous_hgb_equity=previous_hgb_equity,
            current_depreciation_difference=(
                current_depreciation_difference
            ),
            previous_depreciation_difference=(
                previous_depreciation_difference
            ),
            current_book_value_difference=(
                current_book_value_difference
            ),
            previous_book_value_difference=(
                previous_book_value_difference
            ),
            current_tax_equity=values[
                ("BVV.profitLoss.assetsCurrentYear",)
            ],
            previous_tax_equity=values[
                ("BVV.profitLoss.assetsPreviousYear",)
            ],
            contribution=contribution,
            withdrawal_distribution=(
                withdrawal_distribution
            ),
            profit_loss=values[
                ("BVV.profitLoss",)
            ],
        )

    def opening_hgb_equity(
        self,
        *,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> Decimal:
        """Ermittelt das HGB-Eigenkapital zu Beginn des Geschäftsjahres."""

        control_accounts, _, _ = self.load_account_configuration()

        report = self.build_trial_balance_report(
            start_date=self._context.fiscal_year.start_date,
            end_date=self._context.fiscal_year.end_date,
            opening_balance_account_number=(
                control_accounts.opening_balance_account
            ),
        )

        mapping_rules = {
            rule.account_number: rule
            for rule in chart_of_accounts.account_mapping_rules
        }

        opening_equity = Decimal("0.00")

        for row in report.rows:
            opening_balance = (
                row.opening_credit
                - row.opening_debit
            )

            if opening_balance == Decimal("0.00"):
                continue

            mapping_rule = mapping_rules.get(
                row.account_number
            )

            if mapping_rule is None:
                continue

            position = (
                mapping_rule.credit_position
                if opening_balance > Decimal("0.00")
                else mapping_rule.debit_position
            )

            if position is None:
                continue

            if not position.code.startswith(
                "HGB.266.PASSIVA.A"
            ):
                continue

            opening_equity += opening_balance

        return opening_equity

    def load_account_taxonomy_concepts(
        self,
    ) -> dict[str, str]:
        """Lädt die mandantenspezifischen Konten-Taxonomiezuordnungen."""

        if self._chart_of_accounts_repository is None:
            raise ValueError(
                "Kontenrahmen-Repository ist nicht verfügbar."
            )

        return (
            self._chart_of_accounts_repository
            .load_account_taxonomy_concepts(
                self._context.company.company_id,
                taxonomy_version="6.9",
            )
        )

    def save_account_taxonomy_concept(
        self,
        *,
        account_number: str,
        concept_name: str | None,
    ) -> None:
        """Speichert oder entfernt die Taxonomiezuordnung eines Kontos."""

        if self._chart_of_accounts_repository is None:
            raise ValueError(
                "Kontenrahmen-Repository ist nicht verfügbar."
            )

        self._chart_of_accounts_repository.save_single_account_taxonomy_concept(
            company_id=self._context.company.company_id,
            taxonomy_version="6.9",
            account_number=account_number,
            concept_name=concept_name,
        )

    def account_taxonomy_choices(
        self,
        *,
        account_number: str,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> tuple[tuple[str, str], ...]:
        """Liefert zulässige Taxonomiezuordnungen eines Kontos."""

        mapping_rule = next(
            (
                rule
                for rule in chart_of_accounts.account_mapping_rules
                if rule.account_number == account_number
            ),
            None,
        )

        if mapping_rule is None:
            raise ValueError(
                "Für Konto "
                f"{account_number} ist keine HGB-Zuordnung "
                "vorhanden."
            )

        debit_position = mapping_rule.debit_position
        credit_position = mapping_rule.credit_position

        if debit_position is None:
            position = credit_position
        elif credit_position is None:
            position = debit_position
        elif debit_position == credit_position:
            position = debit_position
        else:
            raise ValueError(
                "Für Konto "
                f"{account_number} sind unterschiedliche "
                "HGB-Zuordnungen für Soll und Haben "
                "hinterlegt. Die E-Bilanz-Zuordnung kann "
                "deshalb nicht eindeutig bestimmt werden."
            )

        if position is None:
            raise ValueError(
                "Für Konto "
                f"{account_number} ist keine HGB-Zuordnung "
                "vorhanden."
            )

        return self._e_bilanz_service.account_taxonomy_choices(
            fiscal_year=self._context.fiscal_year,
            position=position,
        )

    def build_fixed_asset_schedule(self):
        """Erzeugt den Anlagenspiegel des geöffneten Geschäftsjahres."""

        if self._fixed_asset_schedule_service is None:
            return ()

        bookings = self._booking_repository.list_for_fiscal_year(
            company_id=self._context.company.company_id,
            fiscal_year=self._context.fiscal_year,
        )

        reversed_booking_ids = frozenset(
            booking.reversal_of_booking_id
            for booking in bookings
            if (
                booking.booking_type is BookingType.REVERSAL
                and booking.reversal_of_booking_id is not None
            )
        )

        return self._fixed_asset_schedule_service.build(
            company_id=self._context.company.company_id,
            fiscal_year_start=self._context.fiscal_year.start_date,
            fiscal_year_end=self._context.fiscal_year.end_date,
            reversed_booking_ids=reversed_booking_ids,
        )

    def build_e_bilanz(
        self,
        *,
        preparation: EBilanzPreparationResult,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> EBilanzDocument:
        """Erzeugt die E-Bilanz des geöffneten Geschäftsjahres."""

        if not self.is_closed:
            raise ValueError(
                "Die E-Bilanz kann erst nach dem Jahresabschluss erzeugt werden."
            )

        master_data = self.load_company_master_data()
        entity = EntityIdentifier.from_company(self._context.company)

        (
            control_accounts,
            vat_accounts,
            account_roles,
        ) = self.load_account_configuration()

        account_taxonomy_concepts = (
            self.load_account_taxonomy_concepts()
        )

        account_details = self._e_bilanz_account_detail_service.build_for_e_bilanz(
            pre_closing_ledger=self._pre_closing_ledger,
            closed_ledger=self._ledger,
        )

        fixed_asset_schedule = self.build_fixed_asset_schedule()

        fixed_asset_disposal_details = (
            self.build_fixed_asset_disposal_details(
                control_accounts=control_accounts,
            )
        )

        bvv_evaluation = self.build_bvv_evaluation(
            preparation=preparation,
            chart_of_accounts=chart_of_accounts,
        )

        profit_appropriation_data = None
        previous_profit_loss_carryforward = Decimal("0.00")

        if (
            self._profit_appropriation_annual_data_repository
            is not None
        ):
            profit_appropriation_data = (
                self.load_profit_appropriation_annual_data()
            )

            if profit_appropriation_data is not None:
                previous_profit_loss_carryforward = (
                    self.previous_profit_loss_carryforward()
                )

        shareholders = ()

        if self._shareholder_repository is not None:
            shareholders = (
                self._shareholder_repository.list_for_company(
                    self._context.company.company_id
                )
            )

        document = self._e_bilanz_service.build(
            master_data=master_data,
            fiscal_year=self._context.fiscal_year,
            amounts=preparation.amounts,
            income_statement=preparation.income_statement,
            balance_sheet=preparation.balance_sheet,
            vat_accounts=vat_accounts,
            account_roles=account_roles,
            entity_identifier=entity.value,
            entity_scheme=entity.scheme,
            previous_fiscal_year=self.previous_fiscal_year,
            account_details=account_details,
            account_taxonomy_concepts=(
                account_taxonomy_concepts
            ),
            fixed_asset_schedule=fixed_asset_schedule,
            fixed_asset_disposal_details=(
                fixed_asset_disposal_details
            ),
            shareholders=shareholders,
            current_depreciation_difference=(
                bvv_evaluation.current_depreciation_difference
            ),
            previous_depreciation_difference=(
                bvv_evaluation.previous_depreciation_difference
            ),
            previous_hgb_equity=(
                bvv_evaluation.previous_hgb_equity
            ),
            contribution=(
                bvv_evaluation.contribution
            ),
            withdrawal_distribution=(
                bvv_evaluation.withdrawal_distribution
            ),
            profit_appropriation_data=(
                profit_appropriation_data
            ),
            previous_profit_loss_carryforward=(
                previous_profit_loss_carryforward
            ),
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
