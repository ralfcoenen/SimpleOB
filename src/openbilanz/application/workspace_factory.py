"""Aufbau eines geöffneten OpenBilanz-Geschäftsjahres."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from openbilanz.accounting.financial_statement_context import (
    FinancialStatementContext,
    create_financial_statement_context,
)
from openbilanz.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
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
from openbilanz.database.fixed_asset_repository import FixedAssetRepository
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
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.services.chart_of_accounts_initialization_service import (
    ChartOfAccountsInitializationService,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.depreciation_service import DepreciationService
from openbilanz.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)
from openbilanz.services.e_bilanz_export_service import EBilanzExportService
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationService,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.services.financial_statement_service import (
    FinancialStatementService,
)
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
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
)
from openbilanz.services.vat_revenue_posting_workflow import (
    VatRevenuePostingWorkflow,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.gcd_company_data_mapper import GcdCompanyDataMapper
from openbilanz.taxonomy.resolver import TaxonomyResolver


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Vollständiger Kontext eines geöffneten Geschäftsjahres."""

    workspace: FiscalYearWorkspace
    financial_statement_context: FinancialStatementContext
    financial_statement_service: FinancialStatementService
    closing_accounts: ClosingAccounts
    opening_balance_account_number: str
    control_accounts: AccountingControlAccounts
    vat_accounts: VatAccounts



class WorkspaceFactory:
    """Erzeugt den mandantenspezifischen Arbeitskontext."""

    def __init__(
        self,
        *,
        session: Session,
        company_repository: CompanyRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository,
        vat_configuration_repository: VatConfigurationRepository,
        chart_of_accounts_initialization_service: (
            ChartOfAccountsInitializationService
        ),
        booking_repository: BookingRepository,
        posting_service: PostingService,
        reporting_service: ReportingService,
        closing_consistency_service: ClosingConsistencyService,
        e_bilanz_export_service: EBilanzExportService,
        taxonomy_management_service: TaxonomyManagementService,
        fixed_asset_repository: FixedAssetRepository,
        fixed_asset_depreciation_repository: (
            FixedAssetDepreciationRepository
        ),
        vat_booking_detail_repository: VatBookingDetailRepository,
        vat_revenue_repository: VatRevenueRepository,
        vat_input_timing_repository: VatInputTimingRepository,
        depreciation_service: DepreciationService,
        fixed_asset_depreciation_workflow: (
            FixedAssetDepreciationWorkflow
        ),
        fixed_asset_movement_repository: (
            FixedAssetMovementRepository
        ),
        fixed_asset_loss_workflow: FixedAssetLossWorkflow,
        fixed_asset_disposal_workflow: (
            FixedAssetDisposalWorkflow
        ),
        resolver: TaxonomyResolver,
        arelle_adapter: ArelleAdapter,
        standard_financial_statement_context: FinancialStatementContext,
        position_provider: FinancialStatementPositionProvider,
        vat_revenue_posting_workflow: VatRevenuePostingWorkflow,
    ) -> None:
        self._session = session
        self._company_repository = company_repository
        self._chart_of_accounts_repository = chart_of_accounts_repository
        self._vat_configuration_repository = (
            vat_configuration_repository
        )
        self._chart_of_accounts_initialization_service = (
            chart_of_accounts_initialization_service
        )
        self._booking_repository = booking_repository
        self._vat_booking_detail_repository = (
            vat_booking_detail_repository
        )
        self._vat_revenue_repository = (
            vat_revenue_repository
        )
        self._posting_service = posting_service
        self._reporting_service = reporting_service
        self._closing_consistency_service = closing_consistency_service
        self._e_bilanz_export_service = e_bilanz_export_service
        self._taxonomy_management_service = taxonomy_management_service
        self._fixed_asset_repository = fixed_asset_repository
        self._fixed_asset_depreciation_repository = (
            fixed_asset_depreciation_repository
        )
        self._fixed_asset_movement_repository = (
            fixed_asset_movement_repository
        )
        self._depreciation_service = depreciation_service
        self._fixed_asset_depreciation_workflow = (
            fixed_asset_depreciation_workflow
        )
        self._fixed_asset_movement_repository = (
            fixed_asset_movement_repository
        )
        self._fixed_asset_loss_workflow = (
            fixed_asset_loss_workflow
        )
        self._fixed_asset_disposal_workflow = (
            fixed_asset_disposal_workflow
        )
        self._resolver = resolver
        self._arelle_adapter = arelle_adapter
        self._standard_financial_statement_context = (
            standard_financial_statement_context
        )
        self._position_provider = position_provider
        self._vat_revenue_posting_workflow = (
            vat_revenue_posting_workflow
        )
        self._vat_input_timing_repository = (
            vat_input_timing_repository
        )

    def create(
        self,
        context: ApplicationContext,
    ) -> WorkspaceContext:
        """Erzeugt den Arbeitskontext für Mandant und Geschäftsjahr."""

        initialized = (
            self._chart_of_accounts_initialization_service.initialize(
                company=context.company,
                standard_chart_of_accounts=(
                    self._standard_financial_statement_context
                    .chart_of_accounts
                ),
            )
        )

        if initialized:
            self._session.commit()

        loaded_chart_of_accounts = (
            self._chart_of_accounts_repository.load_for_company(
                company_id=context.company.company_id,
                position_provider=self._position_provider,
            )
        )

        if loaded_chart_of_accounts is None:
            raise RuntimeError(
                "Der Kontenrahmen des Unternehmens "
                "konnte nicht geladen werden."
            )

        chart_of_accounts, accounts = loaded_chart_of_accounts

        control_accounts = (
            self._chart_of_accounts_repository.load_control_accounts(
                context.company.company_id
            )
        )

        vat_accounts = (
            self._chart_of_accounts_repository.load_vat_accounts(
                context.company.company_id
            )
        )

        vat_configuration = (
            self._vat_configuration_repository.load(
                context.company.company_id
            )
        )

        if vat_accounts is None:
            raise RuntimeError(
                "Die Umsatzsteuerkonten des Unternehmens "
                "konnten nicht geladen werden."
            )

        if vat_configuration is None:
            raise RuntimeError(
                "Die Umsatzsteuerkonfiguration des "
                "Unternehmens konnte nicht geladen werden."
            )

        if control_accounts is None:
            raise RuntimeError(
                "Die technischen Konten des Unternehmens "
                "konnten nicht geladen werden."
            )

        standard_context = self._standard_financial_statement_context

        financial_statement_context = create_financial_statement_context(
            assets=standard_context.assets,
            liabilities=standard_context.liabilities,
            income_statement=standard_context.income_statement,
            chart_of_accounts=chart_of_accounts,
            accounts=accounts,
        )

        closing_accounts = ClosingAccounts(
            income_summary_account=(
                control_accounts.income_summary_account
            ),
            profit_account=control_accounts.profit_account,
            loss_account=control_accounts.loss_account,
        )

        closing_service = ClosingService(
            closing_accounts=closing_accounts,
        )

        financial_statement_service = FinancialStatementService(
            closing_service=closing_service,
        )

        closing_workflow = FiscalYearClosingWorkflow(
            session=self._session,
            booking_repository=self._booking_repository,
            company_repository=self._company_repository,
            closing_service=closing_service,
        )

        e_bilanz_preparation_service = EBilanzPreparationService(
            statement_builder=(
                financial_statement_context.statement_builder
            ),
            account_types=financial_statement_context.account_types,
            assets=financial_statement_context.assets,
            liabilities=financial_statement_context.liabilities,
            income_summary_account_number=(
                control_accounts.income_summary_account
            ),
        )

        e_bilanz_account_detail_service = EBilanzAccountDetailService(
            account_mapper=financial_statement_context.account_mapper,
            accounts=financial_statement_context.accounts,
        )

        e_bilanz_service = EBilanzService(
            resolver=self._resolver,
            adapter=self._arelle_adapter,
            company_data_mapper=GcdCompanyDataMapper(),
            assets=financial_statement_context.assets,
            liabilities=financial_statement_context.liabilities,
            income_statement=(
                financial_statement_context.income_statement
            ),
        )

        fixed_asset_reporting_service = (
            FixedAssetReportingService(
                fixed_asset_repository=(
                    self._fixed_asset_repository
                ),
                depreciation_repository=(
                    self._fixed_asset_depreciation_repository
                ),
                movement_repository=(
                    self._fixed_asset_movement_repository
                ),
            )
        )

        fixed_asset_schedule_service = (
            FixedAssetScheduleService(
                fixed_asset_repository=(
                    self._fixed_asset_repository
                ),
                depreciation_repository=(
                    self._fixed_asset_depreciation_repository
                ),
                movement_repository=(
                    self._fixed_asset_movement_repository
                ),
            )
        )

        workspace = FiscalYearWorkspace(
            context=context,
            vat_configuration=vat_configuration,
            booking_repository=self._booking_repository,
            vat_booking_detail_repository=(
                self._vat_booking_detail_repository
            ),
            vat_revenue_repository=(
                self._vat_revenue_repository
            ),
            company_repository=self._company_repository,
            chart_of_accounts_repository=(
                self._chart_of_accounts_repository
            ),
            posting_service=self._posting_service,
            reporting_service=self._reporting_service,
            closing_workflow=closing_workflow,
            closing_consistency_service=(
                self._closing_consistency_service
            ),
            e_bilanz_preparation_service=(
                e_bilanz_preparation_service
            ),
            e_bilanz_account_detail_service=(
                e_bilanz_account_detail_service
            ),
            fixed_asset_schedule_service=(
                fixed_asset_schedule_service
            ),
            e_bilanz_service=e_bilanz_service,
            e_bilanz_export_service=(
                self._e_bilanz_export_service
            ),
            taxonomy_management_service=(
                self._taxonomy_management_service
            ),
            fixed_asset_repository=(
                self._fixed_asset_repository
            ),
            fixed_asset_depreciation_repository=(
                self._fixed_asset_depreciation_repository
            ),
            depreciation_service=(
                self._depreciation_service
            ),
            fixed_asset_depreciation_workflow=(
                self._fixed_asset_depreciation_workflow
            ),
            fixed_asset_movement_repository=(
                self._fixed_asset_movement_repository
            ),
            fixed_asset_reporting_service=(
                fixed_asset_reporting_service
            ),
            fixed_asset_loss_workflow=(
                self._fixed_asset_loss_workflow
            ),
            fixed_asset_disposal_workflow=(
                self._fixed_asset_disposal_workflow
            ),
            vat_revenue_posting_workflow=(
                self._vat_revenue_posting_workflow
            ),
            vat_configuration_repository=(
                self._vat_configuration_repository
            ),
        )

        return WorkspaceContext(
            workspace=workspace,
            financial_statement_context=financial_statement_context,
            financial_statement_service=financial_statement_service,
            closing_accounts=closing_accounts,
            opening_balance_account_number=(
                control_accounts.opening_balance_account
            ),
            control_accounts=control_accounts,
            vat_accounts=vat_accounts,
        )
