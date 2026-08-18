"""Startpunkt der OpenBilanz-Anwendung."""

import tkinter as tk

from openbilanz.accounting.financial_statement_context import (
    create_standard_financial_statement_context,
)
from openbilanz.core.config import load_config
from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Database
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)
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
    EBilanzPreparationService,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy_catalog import TaxonomyCatalog
from openbilanz.taxonomy.taxonomy_downloader import (
    TaxonomyDownloader,
)
from openbilanz.taxonomy.taxonomy_installation_service import (
    TaxonomyInstallationService,
)
from openbilanz.ui.main_window import MainWindow
from openbilanz.ui.start_dialog import StartDialog


def main() -> None:
    """Startet OpenBilanz."""

    config = load_config()

    database = Database(
        config
    )

    database.create_database()

    financial_statement_context = (
        create_standard_financial_statement_context()
    )

    resolver = TaxonomyResolver(
        root=config.taxonomy_dir
    )

    taxonomy_catalog = TaxonomyCatalog(
        root=config.taxonomy_dir
    )

    taxonomy_installation_service = TaxonomyInstallationService(
        target_root=config.taxonomy_dir
    )

    taxonomy_downloader = TaxonomyDownloader()

    taxonomy_management_service = TaxonomyManagementService(
        catalog=taxonomy_catalog,
        installation_service=taxonomy_installation_service,
        download=taxonomy_downloader.download,
    )

    arelle_adapter = ArelleAdapter()

    e_bilanz_preparation_service = (
        EBilanzPreparationService(
            statement_builder=(
                financial_statement_context.statement_builder
            ),
            account_types=(
                financial_statement_context.account_types
            ),
            assets=(
                financial_statement_context.assets
            ),
            liabilities=(
                financial_statement_context.liabilities
            ),
        )
    )

    e_bilanz_account_detail_service = (
        EBilanzAccountDetailService(
            account_mapper=(
                financial_statement_context.account_mapper
            ),
            accounts=(
                financial_statement_context.accounts
            ),
        )
    )

    e_bilanz_service = EBilanzService(
        resolver=resolver,
        adapter=arelle_adapter,
        company_data_mapper=GcdCompanyDataMapper(),
        assets=financial_statement_context.assets,
        liabilities=financial_statement_context.liabilities,
        income_statement=(
            financial_statement_context.income_statement
        ),
    )

    root = tk.Tk()
    root.title("OpenBilanz")

    session = database.create_session()

    try:
        company_repository = CompanyRepository(
            session
        )

        dialog = StartDialog(
            root,
            repository=company_repository,
        )

        root.withdraw()

        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()

        root.wait_window(dialog)

        if dialog.result is None:
            root.destroy()
            return

        context = dialog.result

        root.destroy()

        booking_repository = BookingRepository(
            session
        )


        posting_service = PostingService()

        fixed_asset_repository = FixedAssetRepository(
            session
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
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

        closing_service = ClosingService(
            closing_accounts=ClosingAccounts(
                income_summary_account="8990",
                profit_account="8020",
                loss_account="8021",
            )
        )

        closing_consistency_service = (
            ClosingConsistencyService()
        )

        closing_workflow = FiscalYearClosingWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            closing_service=closing_service,
        )

        e_bilanz_export_service = EBilanzExportService()

        workspace = FiscalYearWorkspace(
            context=context,
            booking_repository=booking_repository,
            company_repository=company_repository,
            posting_service=posting_service,
            closing_workflow=closing_workflow,
            closing_consistency_service=(
                closing_consistency_service
            ),
            e_bilanz_preparation_service=(
                e_bilanz_preparation_service
            ),
            e_bilanz_account_detail_service=(
                e_bilanz_account_detail_service
            ),
            e_bilanz_service=e_bilanz_service,
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
            depreciation_service=(
                depreciation_service
            ),
            fixed_asset_depreciation_workflow=(
                fixed_asset_depreciation_workflow
            ),
        )

        window = MainWindow(
            workspace=workspace,
            financial_statement_context=(
                financial_statement_context
            ),
        )

        window.mainloop()

    finally:
        session.close()
        arelle_adapter.close()
        database.dispose


if __name__ == "__main__":
    main()
