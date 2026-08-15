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
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationService,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.services.posting_service import PostingService
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver
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
            e_bilanz_service=e_bilanz_service,
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
