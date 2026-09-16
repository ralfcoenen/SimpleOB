"""Startpunkt der PySide6-Oberfläche von SimpleOB."""

import sys

from PySide6.QtWidgets import QApplication, QDialog

from openbilanz.core.config import load_config
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Database
from openbilanz.ui_qt.main_window import MainWindow
from openbilanz.ui_qt.start_dialog import StartDialog


def main() -> None:
    """Startet die PySide6-Oberfläche von SimpleOB."""

    app = QApplication(sys.argv)

    config = load_config()

    database = Database(config)
    database.create_database()

    session = database.create_session()

    try:
        company_repository = CompanyRepository(session)

        dialog = StartDialog(
            repository=company_repository,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        context = dialog.result

        if context is None:
            return

        window = MainWindow()
        window.setWindowTitle(
            f"SimpleOB – {context.company.name}"
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
    finally:
        session.close()
        database.dispose()


if __name__ == "__main__":
    main()
