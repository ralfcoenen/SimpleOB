"""Startpunkt der PySide6-Oberfläche von SimpleOB."""

import sys

from PySide6.QtWidgets import QApplication

from openbilanz.ui_qt.main_window import MainWindow


def main() -> None:
    """Startet die PySide6-Oberfläche von SimpleOB."""

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
