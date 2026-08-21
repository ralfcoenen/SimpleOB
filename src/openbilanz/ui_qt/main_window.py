"""Hauptfenster der experimentellen PySide6-Oberfläche."""

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.ui_qt.accounts_page import AccountsPage


class MainWindow(QMainWindow):
    """Hauptfenster der PySide6-Oberfläche."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("OpenBilanz – PySide6")
        self.resize(1100, 700)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self.setCentralWidget(central_widget)

        self._create_tabs()

    def _create_tabs(self) -> None:
        """Erzeugt die Hauptarbeitsbereiche."""

        self._accounts_page = AccountsPage()

        self._tabs.addTab(
            self._accounts_page,
            "Konten",
        )

        for tab_name in (
            "Journal",
            "Buchen",
            "Anlagen",
            "Bilanz",
            "GuV",
            "Auswertungen",
            "Jahresabschluss",
            "E-Bilanz",
        ):
            self._tabs.addTab(QWidget(), tab_name)
