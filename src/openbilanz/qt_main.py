"""Separater Startpunkt für die experimentelle PySide6-Oberfläche."""

import sys
from datetime import timedelta

from PySide6.QtWidgets import QApplication, QDialog

from openbilanz.application.bootstrap import ApplicationBootstrap
from openbilanz.core.context import ApplicationContext
from openbilanz.services.fiscal_year_opening_workflow import (
    FiscalYearOpeningWorkflow,
)
from openbilanz.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from openbilanz.ui_qt.main_window import MainWindow
from openbilanz.ui_qt.start_dialog import StartDialog


def main() -> None:
    """Startet die experimentelle PySide6-Oberfläche."""

    app = QApplication(sys.argv)

    bootstrap = ApplicationBootstrap.create()

    def create_fiscal_year(
        company,
        fiscal_year,
    ) -> None:
        """Legt ein Geschäftsjahr an und eröffnet es aus dem Vorjahr."""

        managed_fiscal_years = (
            bootstrap.company_repository
            .get_managed_fiscal_years(
                company.company_id
            )
        )

        source_fiscal_year = next(
            (
                managed.fiscal_year
                for managed in managed_fiscal_years
                if (
                    managed.fiscal_year.end_date
                    + timedelta(days=1)
                    == fiscal_year.start_date
                )
            ),
            None,
        )

        try:
            bootstrap.company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
                commit=False,
            )

            if source_fiscal_year is None:
                bootstrap.session.commit()
                return

            target_context = (
                bootstrap.workspace_factory.create(
                    ApplicationContext(
                        company=company,
                        fiscal_year=fiscal_year,
                    )
                )
            )

            control_accounts = (
                target_context.control_accounts
            )

            transfer_service = (
                FiscalYearTransferService(
                    opening_balance_account_number=(
                        control_accounts
                        .opening_balance_account
                    ),
                    profit_account_number=(
                        control_accounts.profit_account
                    ),
                    loss_account_number=(
                        control_accounts.loss_account
                    ),
                    retained_earnings_account_number=(
                        control_accounts
                        .retained_earnings_account
                    ),
                )
            )

            opening_workflow = (
                FiscalYearOpeningWorkflow(
                    session=bootstrap.session,
                    booking_repository=(
                        bootstrap.booking_repository
                    ),
                    company_repository=(
                        bootstrap.company_repository
                    ),
                    transfer_service=(
                        transfer_service
                    ),
                    posting_service=(
                        bootstrap.posting_service
                    ),
                )
            )

            opening_workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=fiscal_year,
                account_types=(
                    target_context
                    .financial_statement_context
                    .account_types
                ),
            )

        except Exception:
            bootstrap.session.rollback()
            raise

    try:
        while True:
            dialog = StartDialog(
                repository=(
                    bootstrap.company_repository
                ),
                create_fiscal_year=(
                    create_fiscal_year
                ),
            )

            if (
                dialog.exec()
                != QDialog.DialogCode.Accepted
            ):
                break

            if dialog.result is None:
                break

            application_context = dialog.result

            workspace_context = (
                bootstrap.workspace_factory.create(
                    application_context
                )
            )

            def reload_workspace_context():
                return (
                    bootstrap.workspace_factory.create(
                        application_context
                    )
                )

            window = MainWindow(
                workspace_context=workspace_context,
                reload_workspace_context=(
                    reload_workspace_context
                ),
                pdf_reporting_service=(
                    bootstrap.pdf_reporting_service
                ),
            )

            window.show()

            app.exec()

            if not window.return_to_start_requested:
                break

    finally:
        bootstrap.close()

if __name__ == "__main__":
    main()
