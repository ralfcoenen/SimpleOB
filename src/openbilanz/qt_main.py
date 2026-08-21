"""Separater Startpunkt für die experimentelle PySide6-Oberfläche."""

import sys

from PySide6.QtWidgets import QApplication

from openbilanz.ui_qt.main_window import MainWindow


def main() -> None:
    """Startet die experimentelle PySide6-Oberfläche."""

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
