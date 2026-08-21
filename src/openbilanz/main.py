"""Startpunkt der OpenBilanz-Anwendung."""

import tkinter as tk

from openbilanz.application.bootstrap import ApplicationBootstrap
from openbilanz.ui.main_window import MainWindow
from openbilanz.ui.start_dialog import StartDialog


def main() -> None:
    """Startet OpenBilanz."""

    bootstrap = ApplicationBootstrap.create()

    try:
        while True:
            root = tk.Tk()
            root.title("OpenBilanz")

            dialog = StartDialog(
                root,
                repository=bootstrap.company_repository,
            )

            root.withdraw()

            dialog.deiconify()
            dialog.lift()
            dialog.focus_force()

            root.wait_window(dialog)

            if dialog.result is None:
                root.destroy()
                break

            context = dialog.result

            root.destroy()

            workspace_context = bootstrap.workspace_factory.create(
                context
            )

            window = MainWindow(
                workspace=workspace_context.workspace,
                financial_statement_context=(
                    workspace_context
                    .financial_statement_context
                ),
                closing_accounts=(
                    workspace_context.closing_accounts
                ),
                opening_balance_account_number=(
                    workspace_context
                    .opening_balance_account_number
                ),
                vat_accounts=(
                    workspace_context.vat_accounts
                ),
                pdf_reporting_service=(
                    bootstrap.pdf_reporting_service
                ),
            )

            window.mainloop()

            if not window.return_to_start_requested:
                break

    finally:
        bootstrap.close()


if __name__ == "__main__":
    main()
