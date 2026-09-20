"""Startpunkt der PySide6-Oberfläche von SimpleOB."""

import sys

from PySide6.QtWidgets import QApplication, QDialog

from openbilanz.accounting.financial_statement_context import (
    create_financial_statement_context,
    create_standard_financial_statement_context,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.core.config import load_config
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.bvv_annual_data_repository import (
    BvvAnnualDataRepository,
)
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
from openbilanz.database.shareholder_repository import ShareholderRepository
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)
from openbilanz.eric.elster_bilanz_payload_service import (
    ElsterBilanzPayloadService,
)
from openbilanz.eric.elster_bilanz_transmission_service import (
    ElsterBilanzTransmissionService,
)
from openbilanz.eric.eric_create_th_adapter import EricCreateThAdapter
from openbilanz.eric.eric_send_adapter import EricSendAdapter
from openbilanz.eric.eric_validate_adapter import EricValidateAdapter
from openbilanz.services.chart_of_accounts_initialization_service import (
    ChartOfAccountsInitializationService,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from openbilanz.services.depreciation_service import DepreciationService
from openbilanz.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)
from openbilanz.services.e_bilanz_export_service import EBilanzExportService
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationService,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.fiscal_year_opening_workflow import (
    FiscalYearOpeningWorkflow,
)
from openbilanz.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)
from openbilanz.services.fixed_asset_disposal_workflow import (
    FixedAssetDisposalWorkflow,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetScheduleService,
)
from openbilanz.services.pdf_reporting_service import PdfReportingService
from openbilanz.services.posting_service import PostingService
from openbilanz.services.reporting_service import ReportingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.gcd_company_data_mapper import GcdCompanyDataMapper
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy_catalog import TaxonomyCatalog
from openbilanz.taxonomy.taxonomy_downloader import TaxonomyDownloader
from openbilanz.taxonomy.taxonomy_installation_service import (
    TaxonomyInstallationService,
)
from openbilanz.ui_qt.main_window import MainWindow
from openbilanz.ui_qt.start_dialog import StartDialog


def main() -> None:
    """Startet die PySide6-Oberfläche von SimpleOB."""

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = load_config()

    elster_bilanz_transmission_service = None

    if (
        config.eric_lib_dir is not None
        and config.eric_manufacturer_id is not None
        and config.eric_data_supplier is not None
        and config.eric_certificate_path is not None
        and config.eric_certificate_pin is not None
    ):
        elster_bilanz_transmission_service = (
            ElsterBilanzTransmissionService(
                payload_service=ElsterBilanzPayloadService(),
                create_th_adapter=EricCreateThAdapter(
                    lib_dir=config.eric_lib_dir,
                ),
                validate_adapter=EricValidateAdapter(
                    lib_dir=config.eric_lib_dir,
                ),
                send_adapter=EricSendAdapter(
                    lib_dir=config.eric_lib_dir,
                ),
                manufacturer_id=config.eric_manufacturer_id,
                data_supplier=config.eric_data_supplier,
                certificate_path=config.eric_certificate_path,
                certificate_pin=config.eric_certificate_pin,
            )
        )

    database = Database(config)
    database.create_database()

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
    session = database.create_session()

    try:
        company_repository = CompanyRepository(session)
        shareholder_repository = ShareholderRepository(session)

        chart_of_accounts_repository = ChartOfAccountsRepository(
            session
        )

        chart_of_accounts_initialization_service = (
            ChartOfAccountsInitializationService(
                repository=chart_of_accounts_repository,
                position_provider=position_provider,
            )
        )

        booking_repository = BookingRepository(session)
        posting_service = PostingService()

        fixed_asset_repository = FixedAssetRepository(session)

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(session)
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(session)
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(session)
        )

        fixed_asset_schedule_service = FixedAssetScheduleService(
            fixed_asset_repository=fixed_asset_repository,
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
        )

        depreciation_service = DepreciationService()
        depreciation_booking_service = DepreciationBookingService()

        fixed_asset_depreciation_workflow = (
            FixedAssetDepreciationWorkflow(
                session=session,
                booking_repository=booking_repository,
                depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
                booking_service=depreciation_booking_service,
            )
        )

        fixed_asset_disposal_workflow = (
            FixedAssetDisposalWorkflow(
                session=session,
                booking_repository=booking_repository,
                movement_repository=(
                    fixed_asset_movement_repository
                ),
                fixed_asset_repository=fixed_asset_repository,
            )
        )

        closing_consistency_service = ClosingConsistencyService()
        e_bilanz_export_service = EBilanzExportService()
        reporting_service = ReportingService()
        pdf_reporting_service = PdfReportingService()

        while True:
            dialog = StartDialog(
                repository=company_repository,
            )

            if dialog.exec() != QDialog.DialogCode.Accepted:
                break

            context = dialog.result

            if context is None:
                break

            opening_transfer_request = (
                dialog.opening_transfer_request
            )

            initialized = (
                chart_of_accounts_initialization_service.initialize(
                    company=context.company,
                    standard_chart_of_accounts=(
                        standard_financial_statement_context
                        .chart_of_accounts
                    ),
                )
            )

            if initialized:
                session.commit()

            loaded_chart_of_accounts = (
                chart_of_accounts_repository.load_for_company(
                    company_id=context.company.company_id,
                    position_provider=position_provider,
                )
            )

            if loaded_chart_of_accounts is None:
                raise RuntimeError(
                    "Der Kontenrahmen des Unternehmens "
                    "konnte nicht geladen werden."
                )

            (
                chart_of_accounts,
                accounts,
            ) = loaded_chart_of_accounts

            control_accounts = (
                chart_of_accounts_repository.load_control_accounts(
                    context.company.company_id
                )
            )

            vat_accounts = (
                chart_of_accounts_repository.load_vat_accounts(
                    context.company.company_id
                )
            )

            if vat_accounts is None:
                raise RuntimeError(
                    "Die Umsatzsteuerkonten des Unternehmens "
                    "konnten nicht geladen werden."
                )

            if control_accounts is None:
                raise RuntimeError(
                    "Die technischen Konten des Unternehmens "
                    "konnten nicht geladen werden."
                )

            financial_statement_context = (
                create_financial_statement_context(
                    assets=(
                        standard_financial_statement_context.assets
                    ),
                    liabilities=(
                        standard_financial_statement_context.liabilities
                    ),
                    income_statement=(
                        standard_financial_statement_context
                        .income_statement
                    ),
                    chart_of_accounts=chart_of_accounts,
                    accounts=accounts,
                )
            )

            if opening_transfer_request is not None:
                (
                    target_fiscal_year,
                    source_fiscal_year,
                ) = opening_transfer_request

                if target_fiscal_year != context.fiscal_year:
                    raise RuntimeError(
                        "Das für die Saldenübernahme "
                        "vorgesehene Geschäftsjahr stimmt "
                        "nicht mit dem ausgewählten "
                        "Geschäftsjahr überein."
                    )

                transfer_service = FiscalYearTransferService(
                    opening_balance_account_number=(
                        control_accounts.opening_balance_account
                    ),
                    profit_account_number=(
                        control_accounts.profit_account
                    ),
                    loss_account_number=(
                        control_accounts.loss_account
                    ),
                    profit_loss_carryforward_account_number=(
                        control_accounts
                        .profit_loss_carryforward_account
                    ),
                )

                opening_workflow = FiscalYearOpeningWorkflow(
                    session=session,
                    booking_repository=booking_repository,
                    company_repository=company_repository,
                    transfer_service=transfer_service,
                    posting_service=posting_service,
                )

                opening_workflow.open(
                    company_id=context.company.company_id,
                    source_fiscal_year=source_fiscal_year,
                    target_fiscal_year=target_fiscal_year,
                    account_types=(
                        financial_statement_context.account_types
                    ),
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

            closing_workflow = FiscalYearClosingWorkflow(
                session=session,
                booking_repository=booking_repository,
                company_repository=company_repository,
                closing_service=closing_service,
            )

            e_bilanz_preparation_service = EBilanzPreparationService(
                statement_builder=(
                    financial_statement_context.statement_builder
                ),
                closing_service=closing_service,
                account_types=(
                    financial_statement_context.account_types
                ),
                assets=financial_statement_context.assets,
                liabilities=financial_statement_context.liabilities,
                income_summary_account_number=(
                    control_accounts.income_summary_account
                ),
            )

            e_bilanz_account_detail_service = (
                EBilanzAccountDetailService(
                    account_mapper=(
                        financial_statement_context.account_mapper
                    ),
                    accounts=financial_statement_context.accounts,
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

            bvv_annual_data_repository = BvvAnnualDataRepository(
                session
            )

            workspace = FiscalYearWorkspace(
                context=context,
                booking_repository=booking_repository,
                company_repository=company_repository,
                bvv_annual_data_repository=(
                    bvv_annual_data_repository
                ),
                shareholder_repository=shareholder_repository,
                chart_of_accounts_repository=(
                    chart_of_accounts_repository
                ),
                posting_service=posting_service,
                reporting_service=reporting_service,
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
                e_bilanz_export_service=e_bilanz_export_service,
                taxonomy_management_service=(
                    taxonomy_management_service
                ),
                fixed_asset_repository=fixed_asset_repository,
                fixed_asset_depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
                tax_depreciation_adjustment_repository=(
                    tax_depreciation_adjustment_repository
                ),
                fixed_asset_movement_repository=(
                    fixed_asset_movement_repository
                ),
                fixed_asset_schedule_service=(
                    fixed_asset_schedule_service
                ),
                depreciation_service=depreciation_service,
                fixed_asset_depreciation_workflow=(
                    fixed_asset_depreciation_workflow
                ),
                fixed_asset_disposal_workflow=(
                    fixed_asset_disposal_workflow
                ),
            )

            window = MainWindow(
                context=context,
                workspace=workspace,
                accounts=accounts,
                assets=financial_statement_context.assets,
                liabilities=financial_statement_context.liabilities,
                income_statement=(
                    financial_statement_context.income_statement
                ),
                statement_builder=(
                    financial_statement_context.statement_builder
                ),
                account_types=(
                    financial_statement_context.account_types
                ),
                chart_of_accounts=chart_of_accounts,
                opening_balance_account_number=(
                    control_accounts.opening_balance_account
                ),
                depreciation_expense_account_number=(
                    control_accounts.depreciation_expense_account
                ),
                closing_accounts=closing_accounts,
                closing_service=closing_service,
                account_mapper=(
                    financial_statement_context.account_mapper
                ),
                vat_accounts=vat_accounts,
                pdf_reporting_service=pdf_reporting_service,
                elster_bilanz_transmission_service=(
                    elster_bilanz_transmission_service
                ),
            )
            window.show()

            window.statusBar().showMessage(
                " | ".join(
                    (
                        context.company.name,
                        context.fiscal_year.display_name,
                    )
                )
            )

            app.exec()

            if not window.return_to_start_requested:
                break

    finally:
        session.close()
        arelle_adapter.close()
        database.dispose()


if __name__ == "__main__":
    main()
