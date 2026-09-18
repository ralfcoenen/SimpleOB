"""PySide6-Dialog zur Zuordnung einer Anschaffungsbuchung."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


@dataclass(frozen=True, slots=True)
class AcquisitionBookingCandidate:
    """Eine mögliche Anschaffungsbuchung."""

    booking_id: UUID
    booking_line_position: int
    booking_date_text: str
    voucher_no: str
    description: str
    account_number: str
    amount: Decimal


class FixedAssetAcquisitionLinkDialog(QDialog):
    """Wählt eine vorhandene Anschaffungsbuchung aus."""

    def __init__(
        self,
        parent=None,
        *,
        candidates: tuple[AcquisitionBookingCandidate, ...],
    ) -> None:
        super().__init__(parent)

        self._candidates = candidates
        self.selected_candidate: AcquisitionBookingCandidate | None = None

        self.setWindowTitle(
            "SimpleOB – Anschaffungsbuchung zuordnen"
        )
        self.resize(820, 420)
        self.setMinimumSize(700, 320)

        layout = QVBoxLayout(self)

        instruction = QLabel(
            "Bitte die Buchungszeile auswählen, "
            "die der Anschaffung des Anlageguts entspricht."
        )
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            (
                "Datum",
                "Beleg",
                "Buchungstext",
                "Konto",
                "Betrag",
            )
        )
        self._table.setRowCount(
            len(self._candidates)
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setAlternatingRowColors(True)

        for row, candidate in enumerate(self._candidates):
            values = (
                candidate.booking_date_text,
                candidate.voucher_no,
                candidate.description,
                candidate.account_number,
                f"{candidate.amount:.2f}",
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 4:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self._table.setItem(
                    row,
                    column,
                    item,
                )

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
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        if self._candidates:
            self._table.selectRow(0)

        self._table.doubleClicked.connect(
            self._accept_selection
        )

        layout.addWidget(self._table)

        buttons = QDialogButtonBox()

        cancel_button = buttons.addButton(
            "Abbrechen",
            QDialogButtonBox.ButtonRole.RejectRole,
        )
        link_button = buttons.addButton(
            "Zuordnen",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        cancel_button.clicked.connect(self.reject)
        link_button.clicked.connect(self._accept_selection)

        layout.addWidget(buttons)

    def _accept_selection(self) -> None:
        """Übernimmt die ausgewählte Buchungszeile."""

        row = self._table.currentRow()

        if row < 0 or row >= len(self._candidates):
            return

        self.selected_candidate = self._candidates[row]
        self.accept()
