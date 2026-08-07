"""Hauptfenster der OpenBilanz-Anwendung."""

from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openbilanz.ui.opening_balance_dialog import (
    OpeningBalanceDialog,
)


class MainWindow(QMainWindow):
    """Hauptfenster von OpenBilanz."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("OpenBilanz")
        self.resize(900, 600)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        title = QLabel("OpenBilanz")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        subtitle = QLabel(
            "Buchhaltung und Jahresabschluss"
        )

        opening_balance_button = QPushButton(
            "Eröffnungsbilanz erfassen"
        )
        opening_balance_button.clicked.connect(
            self._open_opening_balance
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(opening_balance_button)
        layout.addStretch()

        self.setCentralWidget(central_widget)

    def _open_opening_balance(self) -> None:
        """Öffnet die Erfassung der Eröffnungsbilanz."""

        dialog = OpeningBalanceDialog(self)
        dialog.exec()
