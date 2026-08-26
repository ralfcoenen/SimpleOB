"""Journalansicht der PySide6-Oberfläche."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.ui_qt.journal_table_model import (
    JournalTableModel,
    JournalTableRow,
)


class JournalPage(QWidget):
    """Arbeitsbereich für das Buchungsjournal."""

    def __init__(
        self,
        *,
        rows: tuple[JournalTableRow, ...],
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Journal")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        self._model = JournalTableModel(
            rows=rows
        )

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setAlternatingRowColors(True)
        self._table.setHorizontalScrollMode(
            QTableWidget.ScrollMode.ScrollPerPixel
        )
        self._table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableView.SelectionMode.SingleSelection
        )
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Interactive,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Interactive,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self._table.setTextElideMode(
            Qt.TextElideMode.ElideRight
        )
        self._table.setHorizontalScrollMode(
            QTableView.ScrollMode.ScrollPerPixel
        )

        layout.addWidget(self._table)

    @property
    def model(self) -> JournalTableModel:
        return self._model
