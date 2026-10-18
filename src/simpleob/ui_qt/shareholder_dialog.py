"""PySide6-Dialoge zur Pflege der Gesellschafterdaten."""

from uuid import UUID

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from simpleob.domain.shareholder import Shareholder
from simpleob.services.fiscal_year_workspace import (
    FiscalYearWorkspace,
)
from simpleob.ui_qt.company_master_data_dialog import (
    FEDERAL_STATES,
)


LEGAL_STATUSES = (
    ("NPP", "Natürliche Person"),
    ("NPB", "Juristische Person"),
)

LEGAL_STATUS_LABELS = {
    code: label
    for code, label in LEGAL_STATUSES
}


class ShareholdersDialog(QDialog):
    """Verwaltet die Gesellschafter eines Unternehmens."""

    def __init__(
        self,
        parent,
        *,
        workspace: FiscalYearWorkspace,
    ) -> None:
        super().__init__(parent)

        self._workspace = workspace
        self._shareholders: dict[UUID, Shareholder] = {}
        self.data_changed = False

        self.setWindowTitle("SimpleOB – Gesellschafter")
        self.resize(980, 520)
        self.setMinimumSize(850, 450)

        self._create_ui()
        self._reload()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        title_label = QLabel("Gesellschafter")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        company_label = QLabel(
            self._workspace.context.company.name
        )
        layout.addWidget(company_label)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            (
                "Nr.",
                "Name",
                "Vorname",
                "Rechtsstatus",
                "Anteil",
            )
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self._table.cellDoubleClicked.connect(
            self._on_double_click
        )

        layout.addWidget(self._table)

        button_layout = QHBoxLayout()

        add_button = QPushButton("Hinzufügen")
        add_button.clicked.connect(self._add)
        button_layout.addWidget(add_button)

        edit_button = QPushButton("Bearbeiten")
        edit_button.clicked.connect(self._edit)
        button_layout.addWidget(edit_button)

        delete_button = QPushButton("Löschen")
        delete_button.clicked.connect(self._delete)
        button_layout.addWidget(delete_button)

        button_layout.addStretch()

        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _reload(self) -> None:
        """Lädt die Gesellschafter neu."""

        try:
            shareholders = (
                self._workspace.list_shareholders()
            )
        except (RuntimeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Gesellschafter",
                str(exc),
            )
            return

        self._shareholders = {
            shareholder.shareholder_id: shareholder
            for shareholder in shareholders
        }

        self._table.setRowCount(len(shareholders))

        for row, shareholder in enumerate(shareholders):
            values = (
                shareholder.shareholder_number,
                shareholder.name,
                shareholder.first_name,
                LEGAL_STATUS_LABELS.get(
                    shareholder.legal_status,
                    shareholder.legal_status,
                ),
                (
                    f"{shareholder.share_numerator}"
                    f"/{shareholder.share_denominator}"
                ),
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(
                        256,
                        shareholder.shareholder_id,
                    )

                self._table.setItem(
                    row,
                    column,
                    item,
                )

        self._table.resizeRowsToContents()

    def _selected_shareholder(
        self,
    ) -> Shareholder | None:
        """Liefert den ausgewählten Gesellschafter."""

        row = self._table.currentRow()

        if row < 0:
            return None

        item = self._table.item(row, 0)

        if item is None:
            return None

        shareholder_id = item.data(256)

        if not isinstance(shareholder_id, UUID):
            return None

        return self._shareholders.get(
            shareholder_id
        )

    def _add(self) -> None:
        """Legt einen neuen Gesellschafter an."""

        dialog = ShareholderEditDialog(
            self,
            company_id=(
                self._workspace.context.company.company_id
            ),
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace.add_shareholder(
                dialog.result
            )
        except (RuntimeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Gesellschafter",
                str(exc),
            )
            return

        self.data_changed = True
        self._reload()

    def _edit(self) -> None:
        """Bearbeitet den ausgewählten Gesellschafter."""

        shareholder = self._selected_shareholder()

        if shareholder is None:
            QMessageBox.information(
                self,
                "Gesellschafter",
                "Bitte wählen Sie zuerst einen Gesellschafter aus.",
            )
            return

        dialog = ShareholderEditDialog(
            self,
            company_id=(
                self._workspace.context.company.company_id
            ),
            shareholder=shareholder,
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace.update_shareholder(
                dialog.result
            )
        except (RuntimeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Gesellschafter",
                str(exc),
            )
            return

        self.data_changed = True
        self._reload()

    def _delete(self) -> None:
        """Löscht den ausgewählten Gesellschafter."""

        shareholder = self._selected_shareholder()

        if shareholder is None:
            QMessageBox.information(
                self,
                "Gesellschafter",
                "Bitte wählen Sie zuerst einen Gesellschafter aus.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Gesellschafter löschen",
            (
                "Soll der Gesellschafter "
                f'"{self._display_name(shareholder)}" '
                "wirklich gelöscht werden?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._workspace.delete_shareholder(
                shareholder.shareholder_id
            )
        except (RuntimeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Gesellschafter",
                str(exc),
            )
            return

        self.data_changed = True
        self._reload()

    def _on_double_click(
        self,
        _row: int,
        _column: int,
    ) -> None:
        """Öffnet den ausgewählten Eintrag zur Bearbeitung."""

        if self._selected_shareholder() is not None:
            self._edit()

    @staticmethod
    def _display_name(
        shareholder: Shareholder,
    ) -> str:
        """Liefert einen lesbaren Gesellschafternamen."""

        if shareholder.first_name:
            return (
                f"{shareholder.first_name} "
                f"{shareholder.name}"
            )

        return shareholder.name


class ShareholderEditDialog(QDialog):
    """Bearbeitet einen einzelnen Gesellschafter."""

    def __init__(
        self,
        parent,
        *,
        company_id: UUID,
        shareholder: Shareholder | None = None,
    ) -> None:
        super().__init__(parent)

        self._company_id = company_id
        self._shareholder = shareholder
        self.result: Shareholder | None = None

        self.setWindowTitle("SimpleOB – Gesellschafter")
        self.resize(620, 650)
        self.setMinimumSize(560, 600)

        self._create_ui()
        self._load_values()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        heading = (
            "Gesellschafter bearbeiten"
            if self._shareholder is not None
            else "Gesellschafter hinzufügen"
        )

        heading_label = QLabel(heading)
        heading_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(heading_label)

        layout.addWidget(
            QLabel("* Pflichtfeld für die E-Bilanz")
        )

        form = QFormLayout()
        layout.addLayout(form)

        self._number_edit = QLineEdit()
        self._name_edit = QLineEdit()
        self._first_name_edit = QLineEdit()
        self._numerator_edit = QLineEdit()
        self._denominator_edit = QLineEdit()
        self._tax_number_edit = QLineEdit()
        self._tax_id_edit = QLineEdit()
        self._wid_edit = QLineEdit()

        form.addRow(
            "Gesellschafter-Nr. *",
            self._number_edit,
        )
        form.addRow(
            "Name *",
            self._name_edit,
        )
        form.addRow(
            "Vorname",
            self._first_name_edit,
        )
        form.addRow(
            "Anteil Zähler *",
            self._numerator_edit,
        )
        form.addRow(
            "Anteil Nenner *",
            self._denominator_edit,
        )
        form.addRow(
            "Steuernummer",
            self._tax_number_edit,
        )

        self._tax_number_federal_state_box = QComboBox()
        self._tax_number_federal_state_box.addItem(
            "",
            "",
        )

        for code, name in FEDERAL_STATES:
            self._tax_number_federal_state_box.addItem(
                name,
                code,
            )

        form.addRow(
            "Bundesland der Steuernummer",
            self._tax_number_federal_state_box,
        )

        form.addRow(
            "Steuer-ID",
            self._tax_id_edit,
        )
        form.addRow(
            "Wirtschafts-ID",
            self._wid_edit,
        )

        self._legal_status_box = QComboBox()

        for code, label in LEGAL_STATUSES:
            self._legal_status_box.addItem(
                label,
                code,
            )

        form.addRow(
            "Rechtsstatus *",
            self._legal_status_box,
        )

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Speichern")
        save_button.clicked.connect(self._save)
        save_button.setDefault(True)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _load_values(self) -> None:
        """Übernimmt vorhandene Gesellschafterdaten."""

        if self._shareholder is None:
            self._numerator_edit.setText("1")
            self._denominator_edit.setText("1")

            index = self._legal_status_box.findData("NPP")
            if index >= 0:
                self._legal_status_box.setCurrentIndex(index)

            return

        self._number_edit.setText(
            self._shareholder.shareholder_number
        )
        self._name_edit.setText(
            self._shareholder.name
        )
        self._first_name_edit.setText(
            self._shareholder.first_name
        )
        self._numerator_edit.setText(
            self._shareholder.share_numerator
        )
        self._denominator_edit.setText(
            self._shareholder.share_denominator
        )
        self._tax_number_edit.setText(
            self._shareholder.tax_number
        )
        self._tax_id_edit.setText(
            self._shareholder.tax_id
        )
        self._wid_edit.setText(
            self._shareholder.wid
        )

        index = self._tax_number_federal_state_box.findData(
            self._shareholder.tax_number_federal_state
        )
        if index >= 0:
            self._tax_number_federal_state_box.setCurrentIndex(
                index
            )

        index = self._legal_status_box.findData(
            self._shareholder.legal_status
        )
        if index >= 0:
            self._legal_status_box.setCurrentIndex(
                index
            )

    def _save(self) -> None:
        """Erzeugt den eingegebenen Gesellschafter."""

        values = {
            "company_id": self._company_id,
            "shareholder_number": (
                self._number_edit.text().strip()
            ),
            "name": self._name_edit.text().strip(),
            "first_name": (
                self._first_name_edit.text().strip()
            ),
            "legal_status": (
                self._legal_status_box.currentData()
                or ""
            ),
            "share_numerator": (
                self._numerator_edit.text().strip()
            ),
            "share_denominator": (
                self._denominator_edit.text().strip()
            ),
            "tax_number": (
                self._tax_number_edit.text().strip()
            ),
            "tax_number_federal_state": (
                self._tax_number_federal_state_box.currentData()
                or ""
            ),
            "tax_id": self._tax_id_edit.text().strip(),
            "wid": self._wid_edit.text().strip(),
        }

        try:
            if self._shareholder is not None:
                shareholder = Shareholder(
                    shareholder_id=(
                        self._shareholder.shareholder_id
                    ),
                    **values,
                )
            else:
                shareholder = Shareholder(
                    **values,
                )

        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Ungültige Gesellschafterdaten",
                str(exc),
            )
            return

        self.result = shareholder
        self.accept()
