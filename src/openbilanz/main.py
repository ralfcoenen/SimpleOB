"""Startpunkt der OpenBilanz-Anwendung."""

import sys

from PySide6.QtWidgets import QApplication

from openbilanz.ui.main_window import MainWindow


def main() -> int:
    """Startet OpenBilanz."""

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
