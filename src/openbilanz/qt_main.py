"""Separater Startpunkt für die experimentelle PySide6-Oberfläche."""

import sys

from PySide6.QtWidgets import QApplication, QDialog

from openbilanz.application.bootstrap import ApplicationBootstrap
from openbilanz.ui_qt.main_window import MainWindow
from openbilanz.ui_qt.start_dialog import StartDialog


def main() -> None:
    """Startet die experimentelle PySide6-Oberfläche."""

    app = QApplication(sys.argv)

    bootstrap = ApplicationBootstrap.create()

    try:
        dialog = StartDialog(
            repository=bootstrap.company_repository
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.result is None:
            return

        application_context = dialog.result

        workspace_context = (
            bootstrap.workspace_factory.create(
                application_context
            )
        )

        def reload_workspace_context():
            return bootstrap.workspace_factory.create(
                application_context
            )

        window = MainWindow(
            workspace_context=workspace_context,
            reload_workspace_context=(
                reload_workspace_context
            ),
        )
        window.show()

        app.exec()

    finally:
        bootstrap.close()


if __name__ == "__main__":
    main()
