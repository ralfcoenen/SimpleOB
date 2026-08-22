"""Kontenübersicht der PySide6-Oberfläche."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.account import Account
from openbilanz.ui_qt.accounts_table_model import (
    AccountsTableModel,
    AccountTableRow,
)


class AccountsPage(QWidget):
    """Arbeitsbereich für die Kontenübersicht."""

    new_account_requested = Signal()
    edit_account_requested = Signal()

    def __init__(
        self,
        *,
        rows: tuple[AccountTableRow, ...],
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Kontenübersicht")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        buttons = QHBoxLayout()

        self._new_account_button = QPushButton(
            "Neues Konto"
        )
        self._new_account_button.clicked.connect(
            self.new_account_requested.emit
        )
        buttons.addWidget(
            self._new_account_button
        )

        self._edit_account_button = QPushButton(
            "Konto bearbeiten"
        )
        self._edit_account_button.clicked.connect(
            self.edit_account_requested.emit
        )
        buttons.addWidget(
            self._edit_account_button
        )

        buttons.addStretch()

        layout.addLayout(buttons)

        self._model = AccountsTableModel(
            rows=rows
        )

        self._table = QTableView()
        self._table.setModel(self._model)

        self._table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableView.SelectionMode.SingleSelection
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(False)

        self._table.doubleClicked.connect(
            lambda _index: (
                self.edit_account_requested.emit()
            )
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

        for column in (2, 3, 4):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        self._table.setTextElideMode(
            Qt.TextElideMode.ElideRight
        )

        layout.addWidget(self._table)

    @property
    def model(self) -> AccountsTableModel:
        return self._model

    def selected_account(self) -> Account | None:
        """Liefert das aktuell ausgewählte Konto."""

        selection_model = self._table.selectionModel()

        if selection_model is None:
            return None

        selected_rows = selection_model.selectedRows()

        if not selected_rows:
            return None

        return self._model.account_at(
            selected_rows[0].row()
        )

    def set_editing_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert oder deaktiviert Kontenänderungen."""

        self._new_account_button.setEnabled(enabled)
        self._edit_account_button.setEnabled(enabled)
