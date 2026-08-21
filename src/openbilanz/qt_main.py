"""Separater Startpunkt für die experimentelle PySide6-Oberfläche."""

import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


def main() -> None:
    """Startet die experimentelle PySide6-Oberfläche."""

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("OpenBilanz – PySide6")
    window.resize(900, 600)

    label = QLabel("OpenBilanz – PySide6-Prototyp")
    window.setCentralWidget(label)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
