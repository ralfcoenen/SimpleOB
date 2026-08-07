"""Dialog zur Erfassung der Eröffnungsbilanz."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class OpeningBalanceDialog(QDialog):
    """Erfasst die Anfangsbestände einer Buchhaltung."""

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Eröffnungsbilanz")
        self.resize(800, 500)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        title = QLabel("Eröffnungsbilanz")
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        description = QLabel(
            "Erfassen Sie die Anfangsbestände "
            "der Bilanzkonten."
        )

        self._table = QTableWidget(
            3,
            3,
        )
        self._table.setHorizontalHeaderLabels(
            (
                "Konto",
                "Bezeichnung",
                "Anfangsbestand",
            )
        )

        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self._set_account_row(
            row=0,
            account_number="1200",
            name="Bank",
        )
        self._set_account_row(
            row=1,
            account_number="1600",
            name="Verbindlichkeiten",
        )
        self._set_account_row(
            row=2,
            account_number="1800",
            name="Eigenkapital",
        )

        self._assets_label = QLabel(
            "Aktiva: 0,00 €"
        )
        self._liabilities_label = QLabel(
            "Passiva: 0,00 €"
        )
        self._difference_label = QLabel(
            "Differenz: 0,00 €"
        )

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )

        self._buttons.accepted.connect(
            self.accept
        )
        self._buttons.rejected.connect(
            self.reject
        )

        ok_button = self._buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        ok_button.setText("Übernehmen")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(10)
        layout.addWidget(self._table)
        layout.addWidget(self._assets_label)
        layout.addWidget(self._liabilities_label)
        layout.addWidget(self._difference_label)
        layout.addWidget(self._buttons)

    def _set_account_row(
        self,
        *,
        row: int,
        account_number: str,
        name: str,
    ) -> None:
        """Füllt eine Kontozeile."""

        number_item = QTableWidgetItem(
            account_number
        )
        number_item.setFlags(
            number_item.flags()
            & ~Qt.ItemFlag.ItemIsEditable
        )

        name_item = QTableWidgetItem(name)
        name_item.setFlags(
            name_item.flags()
            & ~Qt.ItemFlag.ItemIsEditable
        )

        amount_item = QTableWidgetItem("0,00")

        self._table.setItem(
            row,
            0,
            number_item,
        )
        self._table.setItem(
            row,
            1,
            name_item,
        )
        self._table.setItem(
            row,
            2,
            amount_item,
        )
