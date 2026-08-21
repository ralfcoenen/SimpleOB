"""Kontenübersicht der PySide6-Oberfläche."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from openbilanz.ui_qt.accounts_table_model import AccountsTableModel


class AccountsPage(QWidget):
    """Arbeitsbereich für die Kontenübersicht."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Kontenübersicht")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        self._model = AccountsTableModel()

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
