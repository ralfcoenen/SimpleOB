"""Gemeinsame Initialisierung der OpenBilanz-Anwendung."""

from dataclasses import dataclass

from openbilanz.accounting.financial_statement_context import (
    create_standard_financial_statement_context,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.application.workspace_factory import WorkspaceFactory
from openbilanz.core.config import load_config
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Database
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import FixedAssetRepository
from openbilanz.database.migration_service import (
    MigrationService,
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
from openbilanz.services.chart_of_accounts_initialization_service import (
    ChartOfAccountsInitializationService,
)
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from openbilanz.services.depreciation_service import DepreciationService
from openbilanz.services.e_bilanz_export_service import EBilanzExportService
from openbilanz.services.fixed_asset_book_value_service import (
    FixedAssetBookValueService,
)
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)
from openbilanz.services.fixed_asset_disposal_booking_service import (
    FixedAssetDisposalBookingService,
)
from openbilanz.services.fixed_asset_disposal_workflow import (
    FixedAssetDisposalWorkflow,
)
from openbilanz.services.fixed_asset_loss_booking_service import (
    FixedAssetLossBookingService,
)
from openbilanz.services.fixed_asset_loss_workflow import (
    FixedAssetLossWorkflow,
)
from openbilanz.services.pdf_reporting_service import PdfReportingService
from openbilanz.services.posting_service import PostingService
from openbilanz.services.reporting_service import ReportingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
)
from openbilanz.services.vat_revenue_posting_workflow import (
    VatRevenuePostingWorkflow,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy_catalog import TaxonomyCatalog
from openbilanz.taxonomy.taxonomy_downloader import TaxonomyDownloader
from openbilanz.taxonomy.taxonomy_installation_service import (
    TaxonomyInstallationService,
)


@dataclass(slots=True)
class ApplicationBootstrap:
    """Gemeinsam genutzte Laufzeitabhängigkeiten von OpenBilanz."""

    database: Database
    arelle_adapter: ArelleAdapter
    session: object
    company_repository: CompanyRepository
    booking_repository: BookingRepository
    posting_service: PostingService
    workspace_factory: WorkspaceFactory
    pdf_reporting_service: PdfReportingService

    @classmethod
    def create(cls) -> "ApplicationBootstrap":
        """Erzeugt die gemeinsamen Laufzeitabhängigkeiten."""

        config = load_config()

        MigrationService(
            config=config
        ).upgrade_to_head()

        database = Database(config)

        standard_financial_statement_context = (
            create_standard_financial_statement_context()
        )

        position_provider = HgbFinancialStatementPositionProvider(
            (
                standard_financial_statement_context.assets,
                standard_financial_statement_context.liabilities,
                standard_financial_statement_context.income_statement,
            )
        )

        resolver = TaxonomyResolver(
            root=config.taxonomy_dir
        )

        taxonomy_catalog = TaxonomyCatalog(
            root=config.taxonomy_dir
        )

        taxonomy_installation_service = (
            TaxonomyInstallationService(
                target_root=config.taxonomy_dir
            )
        )

        taxonomy_downloader = TaxonomyDownloader()

        taxonomy_management_service = (
            TaxonomyManagementService(
                catalog=taxonomy_catalog,
                installation_service=(
                    taxonomy_installation_service
                ),
                download=taxonomy_downloader.download,
            )
        )

        arelle_adapter = ArelleAdapter()

        session = database.create_session()

        company_repository = CompanyRepository(
            session
        )

        chart_of_accounts_repository = (
            ChartOfAccountsRepository(
                session
            )
        )

        vat_configuration_repository = (
            VatConfigurationRepository(
                session
            )
        )

        chart_of_accounts_initialization_service = (
            ChartOfAccountsInitializationService(
                repository=chart_of_accounts_repository,
                position_provider=position_provider,
            )
        )

        booking_repository = BookingRepository(
            session
        )

        vat_revenue_repository = VatRevenueRepository(
            session
        )

        vat_booking_detail_repository = (
            VatBookingDetailRepository(
                session
            )
        )

        vat_input_timing_repository = (
            VatInputTimingRepository(
                session
            )
        )

        vat_revenue_posting_workflow = (
            VatRevenuePostingWorkflow(
                session=session,
                booking_repository=booking_repository,
                vat_booking_detail_repository=(
                    vat_booking_detail_repository
                ),
                vat_revenue_repository=vat_revenue_repository,
                vat_input_timing_repository=(
                    vat_input_timing_repository
                ),
            )
        )

        posting_service = PostingService()

        fixed_asset_repository = (
            FixedAssetRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        depreciation_service = DepreciationService()

        depreciation_booking_service = (
            DepreciationBookingService()
        )

        fixed_asset_depreciation_workflow = (
            FixedAssetDepreciationWorkflow(
                session=session,
                booking_repository=booking_repository,
                depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
                booking_service=(
                    depreciation_booking_service
                ),
            )
        )

        fixed_asset_book_value_service = (
            FixedAssetBookValueService(
                depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
            )
        )

        fixed_asset_loss_booking_service = (
            FixedAssetLossBookingService()
        )

        fixed_asset_loss_workflow = FixedAssetLossWorkflow(
            session=session,
            fixed_asset_repository=fixed_asset_repository,
            depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            movement_repository=(
                fixed_asset_movement_repository
            ),
            booking_repository=booking_repository,
            depreciation_service=depreciation_service,
            book_value_service=(
                fixed_asset_book_value_service
            ),
            booking_service=(
                fixed_asset_loss_booking_service
            ),
        )

        fixed_asset_disposal_booking_service = (
            FixedAssetDisposalBookingService()
        )

        fixed_asset_disposal_workflow = (
            FixedAssetDisposalWorkflow(
                session=session,
                fixed_asset_repository=(
                    fixed_asset_repository
                ),
                depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
                movement_repository=(
                    fixed_asset_movement_repository
                ),
                booking_repository=booking_repository,
                depreciation_service=depreciation_service,
                book_value_service=(
                    fixed_asset_book_value_service
                ),
                booking_service=(
                    fixed_asset_disposal_booking_service
                ),
            )
        )

        closing_consistency_service = (
            ClosingConsistencyService()
        )

        e_bilanz_export_service = (
            EBilanzExportService()
        )

        reporting_service = ReportingService()

        pdf_reporting_service = (
            PdfReportingService()
        )

        workspace_factory = WorkspaceFactory(
            session=session,
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_of_accounts_repository
            ),
            vat_configuration_repository=(
                vat_configuration_repository
            ),
            chart_of_accounts_initialization_service=(
                chart_of_accounts_initialization_service
            ),
            booking_repository=booking_repository,
            vat_booking_detail_repository=(
                vat_booking_detail_repository
            ),
            vat_revenue_repository=(
                vat_revenue_repository
            ),
            vat_input_timing_repository=(
                vat_input_timing_repository
            ),
            posting_service=posting_service,
            reporting_service=reporting_service,
            closing_consistency_service=(
                closing_consistency_service
            ),
            e_bilanz_export_service=(
                e_bilanz_export_service
            ),
            taxonomy_management_service=(
                taxonomy_management_service
            ),
            fixed_asset_repository=(
                fixed_asset_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            depreciation_service=(
                depreciation_service
            ),
            fixed_asset_depreciation_workflow=(
                fixed_asset_depreciation_workflow
            ),
            fixed_asset_loss_workflow=(
                fixed_asset_loss_workflow
            ),
            fixed_asset_disposal_workflow=(
                fixed_asset_disposal_workflow
            ),
            resolver=resolver,
            arelle_adapter=arelle_adapter,
            standard_financial_statement_context=(
                standard_financial_statement_context
            ),
            position_provider=position_provider,
            vat_revenue_posting_workflow=(
                vat_revenue_posting_workflow
            ),
        )

        return cls(
            database=database,
            arelle_adapter=arelle_adapter,
            session=session,
            company_repository=company_repository,
            booking_repository=booking_repository,
            posting_service=posting_service,
            workspace_factory=workspace_factory,
            pdf_reporting_service=pdf_reporting_service,
        )

    def close(self) -> None:
        """Gibt die gemeinsam genutzten Ressourcen frei."""

        self.session.close()
        self.arelle_adapter.close()
        self.database.dispose()
